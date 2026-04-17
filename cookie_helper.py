import os
import configparser
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "claude-usage-linux"
SESSION_KEY_FILE = CONFIG_DIR / "session_key"


def get_session_key() -> str:
    """Return the Claude.ai sessionKey cookie from Chrome or a manual override file."""
    manual = _read_manual_session_key()
    if manual:
        return manual

    return _extract_from_chrome()


def _extract_from_chrome() -> str:
    try:
        import browser_cookie3
        jar = browser_cookie3.chrome(domain_name='.claude.ai')
        for cookie in jar:
            if cookie.name == 'sessionKey':
                return cookie.value
        raise RuntimeError("sessionKey cookie not found in Chrome. Make sure you are logged in to claude.ai in Chrome.")
    except ImportError:
        raise RuntimeError("browser-cookie3 not installed. Run: pip3 install browser-cookie3")


def _read_manual_session_key() -> str:
    if SESSION_KEY_FILE.exists():
        key = SESSION_KEY_FILE.read_text().strip()
        if key:
            return key
    return ""


def save_manual_session_key(key: str):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_KEY_FILE.write_text(key.strip())
