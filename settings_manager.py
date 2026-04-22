"""SettingsManager — stores and manages user preferences in config.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "claude-usage-linux"
CONFIG_FILE = CONFIG_DIR / "config.json"

VALID_INTERVALS_MS = [60000, 300000, 900000, 1800000]
DEFAULT_INTERVAL_MS = 300000


class SettingsManager:
    """Manages settings stored under the 'settings' key in
    ~/.config/claude-usage-linux/config.json.

    Reads the full file and merges its key back on save to avoid clobbering
    keys owned by other managers (e.g. AccountManager's 'accounts' key).
    """

    def __init__(self, config_path: Path = CONFIG_FILE) -> None:
        self._config_path = config_path
        self._refresh_interval_ms: int = DEFAULT_INTERVAL_MS

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load settings from config.json. Falls back to defaults on missing/corrupt file."""
        raw: dict = {}
        try:
            raw = json.loads(self._config_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read config file (%s); using defaults.", exc)

        settings = raw.get("settings", {})
        self._refresh_interval_ms = settings.get("refresh_interval_ms", DEFAULT_INTERVAL_MS)

    def save(self) -> None:
        """Persist settings back to config.json, merging with existing keys."""
        raw: dict = {}
        try:
            raw = json.loads(self._config_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read config file before save (%s); overwriting.", exc)

        raw["settings"] = {"refresh_interval_ms": self._refresh_interval_ms}

        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._config_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(raw, indent=2), encoding="utf-8")
            tmp.chmod(0o600)
            tmp.replace(self._config_path)
        except OSError as exc:
            logger.error("Failed to write config file: %s", exc)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def refresh_interval_ms(self) -> int:
        """Return the current refresh interval in milliseconds."""
        return self._refresh_interval_ms

    def set_refresh_interval_ms(self, ms: int) -> None:
        """Set the refresh interval in milliseconds.

        Raises ValueError if ms is outside [60000, 1800000].
        """
        if ms < 60000 or ms > 1800000:
            raise ValueError(
                f"Refresh interval {ms} ms is out of range; must be between 60000 and 1800000 ms."
            )
        self._refresh_interval_ms = ms
