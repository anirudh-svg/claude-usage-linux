"""Unit tests for startup and structural behavior.

Feature: claude-usage-enhancements
Requirements: 2.10, 2.12, 3.3, 3.4, 4.3, 4.5
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from account_manager import Account, AccountManager
from settings_manager import SettingsManager, VALID_INTERVALS_MS, DEFAULT_INTERVAL_MS

# ---------------------------------------------------------------------------
# GTK availability check (used for tests 3 and 4)
# ---------------------------------------------------------------------------

gi_available = False
try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    gi_available = bool(Gtk.init_check([])[0])
except Exception:
    gi_available = False


# ---------------------------------------------------------------------------
# Test 1: AccountManager startup with absent config
# Validates: Requirements 2.12
# ---------------------------------------------------------------------------

def test_account_manager_absent_config_returns_empty(tmp_path: Path) -> None:
    """load() on a non-existent file returns empty accounts list and None active account."""
    config_path = tmp_path / "nonexistent.json"
    mgr = AccountManager(config_path=config_path)
    mgr.load()

    assert mgr.accounts() == []
    assert mgr.active_account() is None


# ---------------------------------------------------------------------------
# Test 2: AccountManager startup with valid config
# Validates: Requirements 2.11
# ---------------------------------------------------------------------------

def test_account_manager_valid_config_sets_active(tmp_path: Path) -> None:
    """Loading a config with one account sets it as active correctly."""
    config_path = tmp_path / "config.json"
    config_data = {
        "accounts": [{"label": "Personal", "session_key": "sk-ant-test123"}],
        "active_account": "Personal",
    }
    config_path.write_text(json.dumps(config_data))

    mgr = AccountManager(config_path=config_path)
    mgr.load()

    assert len(mgr.accounts()) == 1
    assert mgr.accounts()[0].label == "Personal"
    assert mgr.accounts()[0].session_key == "sk-ant-test123"
    assert mgr.active_account() is not None
    assert mgr.active_account().label == "Personal"


# ---------------------------------------------------------------------------
# Test 3: SessionKeyDialog structure
# Validates: Requirements 4.3, 4.5
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not gi_available, reason="No GTK display available")
def test_session_key_dialog_has_required_widgets() -> None:
    """When GTK is available, verify the dialog has label entry, key entry, Save and Cancel buttons."""
    from session_key_dialog import SessionKeyDialog

    dialog = SessionKeyDialog(parent=None, label="Test", session_key="sk-ant-abc")

    # Verify label entry and key entry exist and are Gtk.Entry instances
    assert isinstance(dialog._label_entry, Gtk.Entry)
    assert isinstance(dialog._key_entry, Gtk.Entry)

    # Verify Save and Cancel buttons exist in the action area
    action_area = dialog.get_action_area()
    button_labels = [btn.get_label() for btn in action_area.get_children()]
    assert "Save" in button_labels
    assert "Cancel" in button_labels

    dialog.destroy()


# ---------------------------------------------------------------------------
# Test 4: SessionKeyDialog "Add Account" path
# Validates: Requirements 2.6
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not gi_available, reason="No GTK display available")
def test_session_key_dialog_add_account_empty_fields() -> None:
    """Opening with empty args has empty label and key fields."""
    from session_key_dialog import SessionKeyDialog

    dialog = SessionKeyDialog(parent=None, label="", session_key="")

    assert dialog.get_label() == ""
    assert dialog.get_session_key() == ""

    dialog.destroy()


# ---------------------------------------------------------------------------
# Test 5: AccountManager capacity
# Validates: Requirements 2.10
# ---------------------------------------------------------------------------

def test_account_manager_supports_10_accounts(tmp_path: Path) -> None:
    """10 accounts can be added and all retrieved via accounts()."""
    config_path = tmp_path / "config.json"
    mgr = AccountManager(config_path=config_path)

    for i in range(10):
        mgr.add_account(label=f"Account{i}", session_key=f"sk-ant-key{i}")

    result = mgr.accounts()
    assert len(result) == 10
    for i in range(10):
        assert any(a.label == f"Account{i}" and a.session_key == f"sk-ant-key{i}" for a in result)


# ---------------------------------------------------------------------------
# Test 6: SettingsManager default interval
# Validates: Requirements 3.3
# ---------------------------------------------------------------------------

def test_settings_manager_default_interval(tmp_path: Path) -> None:
    """When no config exists, refresh_interval_ms() returns 300000 after load()."""
    config_path = tmp_path / "no_config.json"
    mgr = SettingsManager(config_path=config_path)
    mgr.load()

    assert mgr.refresh_interval_ms() == 300000


# ---------------------------------------------------------------------------
# Test 7: SettingsManager 4 interval options
# Validates: Requirements 3.4
# ---------------------------------------------------------------------------

def test_settings_manager_valid_intervals_has_4_entries() -> None:
    """The VALID_INTERVALS_MS list has exactly 4 entries: [60000, 300000, 900000, 1800000]."""
    assert VALID_INTERVALS_MS == [60000, 300000, 900000, 1800000]
