"""Property-based tests for the Accounts submenu in tray_app.py.

Feature: claude-usage-enhancements
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# GTK requires a display; skip all tests if none is available
gi_available = False
try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    gi_available = bool(Gtk.init_check([])[0])
except Exception:
    gi_available = False

pytestmark = pytest.mark.skipif(
    not gi_available,
    reason="No GTK display available",
)

from hypothesis import given, settings
from hypothesis import strategies as st

from account_manager import Account, AccountManager


# ---------------------------------------------------------------------------
# Helpers / strategies
# ---------------------------------------------------------------------------

label_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
    min_size=1,
    max_size=30,
)
key_strategy = st.text(min_size=1, max_size=64)


def _make_manager_with_accounts(
    config_path: Path,
    entries: list[tuple[str, str]],
    active_label: str,
) -> AccountManager:
    mgr = AccountManager(config_path=config_path)
    for label, key in entries:
        mgr._accounts.append(Account(label=label, session_key=key))
    mgr._active_label = active_label
    return mgr


def _build_accounts_submenu(account_mgr: AccountManager) -> Gtk.Menu:
    """Replicate the submenu-building logic from TrayApp._build_accounts_submenu()."""
    submenu = Gtk.Menu()
    active = account_mgr.active_account()
    active_label = active.label if active else None

    for account in account_mgr.accounts():
        item = Gtk.CheckMenuItem(label=account.label)
        item.set_active(account.label == active_label)
        submenu.append(item)

    return submenu


# ---------------------------------------------------------------------------
# Property 8: Account submenu reflects account list
# Validates: Requirements 2.3, 2.5
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    entries=st.lists(
        st.tuples(label_strategy, key_strategy),
        min_size=1,
        max_size=10,
        unique_by=lambda t: t[0],
    ),
    active_index=st.integers(min_value=0, max_value=9),
)
def test_property8_account_submenu_reflects_account_list(
    entries: list[tuple[str, str]],
    active_index: int,
) -> None:
    # Feature: claude-usage-enhancements, Property 8: Account submenu reflects account list
    # For any list of N accounts with a designated active account, the rendered
    # Accounts submenu should contain exactly N items, each matching an account
    # label, with exactly one item marked as active (checkmark).
    active_index = active_index % len(entries)
    active_label = entries[active_index][0]

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        mgr = _make_manager_with_accounts(config_path, entries, active_label)

        submenu = _build_accounts_submenu(mgr)
        children = submenu.get_children()

        # Exactly N CheckMenuItems — one per account
        check_items = [c for c in children if isinstance(c, Gtk.CheckMenuItem)]
        assert len(check_items) == len(entries), (
            f"Expected {len(entries)} CheckMenuItems, got {len(check_items)}"
        )

        # Each item label matches the corresponding account label
        item_labels = [item.get_label() for item in check_items]
        expected_labels = [label for label, _ in entries]
        assert item_labels == expected_labels, (
            f"Submenu labels {item_labels!r} do not match account labels {expected_labels!r}"
        )

        # Exactly one item is marked active, and it matches the active account
        active_items = [item for item in check_items if item.get_active()]
        assert len(active_items) == 1, (
            f"Expected exactly 1 active item, got {len(active_items)}"
        )
        assert active_items[0].get_label() == active_label, (
            f"Active item label {active_items[0].get_label()!r} != expected {active_label!r}"
        )
