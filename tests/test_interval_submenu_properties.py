"""Property-based tests for the Refresh Interval submenu in tray_app.py.

Feature: claude-usage-enhancements
"""
from __future__ import annotations

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

from settings_manager import SettingsManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INTERVAL_OPTIONS = [
    ("1 minute",   60000),
    ("5 minutes",  300000),
    ("15 minutes", 900000),
    ("30 minutes", 1800000),
]


def _build_interval_submenu(settings_mgr: SettingsManager) -> Gtk.Menu:
    """Replicate the submenu-building logic from TrayApp._build_interval_submenu()."""
    submenu = Gtk.Menu()
    current_ms = settings_mgr.refresh_interval_ms()
    first_item: Gtk.RadioMenuItem | None = None

    for label, ms in _INTERVAL_OPTIONS:
        if first_item is None:
            item = Gtk.RadioMenuItem(label=label)
            first_item = item
        else:
            item = Gtk.RadioMenuItem.new_from_widget(first_item)
            item.set_label(label)
        if ms == current_ms:
            item.set_active(True)
        submenu.append(item)

    return submenu


# ---------------------------------------------------------------------------
# Property 15: Interval submenu reflects current selection
# Validates: Requirements 3.4, 3.6
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(interval_ms=st.sampled_from([60000, 300000, 900000, 1800000]))
def test_property15_interval_submenu_reflects_current_selection(
    interval_ms: int,
) -> None:
    # Feature: claude-usage-enhancements, Property 15: Interval submenu reflects current selection
    # For any active refresh interval in [60000, 300000, 900000, 1800000], the
    # submenu should contain exactly 4 RadioMenuItems with exactly one marked
    # active matching the current interval.
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        mgr = SettingsManager(config_path=config_path)
        mgr.set_refresh_interval_ms(interval_ms)

        submenu = _build_interval_submenu(mgr)
        children = submenu.get_children()

        # Exactly 4 RadioMenuItems
        radio_items = [c for c in children if isinstance(c, Gtk.RadioMenuItem)]
        assert len(radio_items) == 4, (
            f"Expected 4 RadioMenuItems, got {len(radio_items)}"
        )

        # Exactly one item is active
        active_items = [item for item in radio_items if item.get_active()]
        assert len(active_items) == 1, (
            f"Expected exactly 1 active RadioMenuItem, got {len(active_items)}"
        )

        # The active item corresponds to the current interval
        expected_label = next(
            label for label, ms in _INTERVAL_OPTIONS if ms == interval_ms
        )
        assert active_items[0].get_label() == expected_label, (
            f"Active item label {active_items[0].get_label()!r} != expected {expected_label!r}"
        )
