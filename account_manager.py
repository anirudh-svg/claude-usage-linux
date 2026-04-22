"""AccountManager — stores and manages named Claude accounts in config.json."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "claude-usage-linux"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Account:
    label: str
    session_key: str


class AccountManager:
    """Manages accounts stored under the 'accounts' and 'active_account' keys
    in ~/.config/claude-usage-linux/config.json.

    Reads the full file and merges its keys back on save to avoid clobbering
    keys owned by other managers (e.g. SettingsManager's 'settings' key).
    """

    def __init__(self, config_path: Path = CONFIG_FILE) -> None:
        self._config_path = config_path
        self._accounts: list[Account] = []
        self._active_label: str | None = None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load accounts from config.json. Treats missing/corrupt file as empty."""
        raw: dict = {}
        try:
            raw = json.loads(self._config_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read config file (%s); treating as empty.", exc)

        accounts_data = raw.get("accounts", [])
        self._accounts = []
        for entry in accounts_data:
            try:
                self._accounts.append(Account(label=entry["label"], session_key=entry["session_key"]))
            except (KeyError, TypeError):
                logger.warning("Skipping malformed account entry: %r", entry)

        self._active_label = raw.get("active_account") or None
        # Validate that active_label actually exists in the list
        if self._active_label and not any(a.label == self._active_label for a in self._accounts):
            self._active_label = self._accounts[0].label if self._accounts else None

    def save(self) -> None:
        """Persist accounts back to config.json, merging with existing keys."""
        raw: dict = {}
        try:
            raw = json.loads(self._config_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read config file before save (%s); overwriting.", exc)

        raw["accounts"] = [{"label": a.label, "session_key": a.session_key} for a in self._accounts]
        raw["active_account"] = self._active_label

        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            # Write to a temp file then atomically replace, and restrict to owner-only
            # (session keys are sensitive credentials — mode 0o600)
            tmp = self._config_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(raw, indent=2), encoding="utf-8")
            tmp.chmod(0o600)
            tmp.replace(self._config_path)
        except OSError as exc:
            logger.error("Failed to write config file: %s", exc)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def accounts(self) -> list[Account]:
        """Return a copy of the current account list."""
        return list(self._accounts)

    def active_account(self) -> Account | None:
        """Return the currently active Account, or None if none is set."""
        if self._active_label is None:
            return None
        for account in self._accounts:
            if account.label == self._active_label:
                return account
        return None

    def set_active(self, label: str) -> None:
        """Set the active account by label and save. Raises ValueError if not found."""
        if not any(a.label == label for a in self._accounts):
            raise ValueError(f"No account with label {label!r}")
        self._active_label = label
        self.save()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def add_account(self, label: str, session_key: str) -> Account:
        """Append a new account, set it as active, and save. Returns the new Account."""
        account = Account(label=label, session_key=session_key)
        self._accounts.append(account)
        self._active_label = label
        self.save()
        return account

    def remove_account(self, label: str) -> None:
        """Remove an account by label and save.

        Raises ValueError if this is the last account.
        """
        if len(self._accounts) <= 1:
            raise ValueError("At least one account must remain")
        self._accounts = [a for a in self._accounts if a.label != label]
        # If we removed the active account, fall back to the first one
        if self._active_label == label:
            self._active_label = self._accounts[0].label if self._accounts else None
        self.save()

    def update_session_key(self, label: str, session_key: str) -> None:
        """Update the session key for an existing account in-place and save."""
        for account in self._accounts:
            if account.label == label:
                account.session_key = session_key
                self.save()
                return
        raise ValueError(f"No account with label {label!r}")
