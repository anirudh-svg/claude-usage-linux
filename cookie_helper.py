"""cookie_helper — fallback session key extraction.

The primary auth flow now uses SessionKeyDialog + AccountManager (config.json).
This module is kept as a last-resort fallback:
  1. Reads a legacy session_key file (for users who set it up manually before).
  2. Extracts the sessionKey cookie from Chrome's local cookie store.

It is called by TrayApp only when AccountManager has no accounts configured,
to pre-populate the first-run SessionKeyDialog.
"""
from __future__ import annotations

from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "claude-usage-linux"
SESSION_KEY_FILE = CONFIG_DIR / "session_key"


def get_session_key() -> str:
    """Return the Claude.ai sessionKey from the legacy file or Chrome cookies.

    Raises RuntimeError if neither source is available.
    """
    manual = _read_manual_session_key()
    if manual:
        return manual
    return _extract_from_chrome()


def _read_manual_session_key() -> str:
    """Read the legacy ~/.config/claude-usage-linux/session_key file if it exists."""
    if SESSION_KEY_FILE.exists():
        key = SESSION_KEY_FILE.read_text().strip()
        if key:
            return key
    return ""


def _extract_from_chrome() -> str:
    """Extract the sessionKey cookie from Chrome's local cookie store."""
    try:
        import browser_cookie3
        jar = browser_cookie3.chrome(domain_name='.claude.ai')
        for cookie in jar:
            if cookie.name == 'sessionKey':
                return cookie.value
        raise RuntimeError(
            "sessionKey cookie not found in Chrome. "
            "Make sure you are logged in to claude.ai in Chrome."
        )
    except ImportError:
        raise RuntimeError(
            "browser-cookie3 not installed. Run: pip3 install browser-cookie3"
        )
