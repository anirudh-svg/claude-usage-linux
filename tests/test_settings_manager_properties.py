"""Property-based tests for settings_manager.py.

Feature: claude-usage-enhancements
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from settings_manager import SettingsManager, VALID_INTERVALS_MS, DEFAULT_INTERVAL_MS


def _make_manager(config_path: Path) -> SettingsManager:
    return SettingsManager(config_path=config_path)


# ---------------------------------------------------------------------------
# Property 13: Refresh interval round-trip
# Validates: Requirements 3.1, 3.2, 3.7
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(interval=st.sampled_from(VALID_INTERVALS_MS))
def test_property13_refresh_interval_round_trip(interval: int) -> None:
    # Feature: claude-usage-enhancements, Property 13: Refresh interval round-trip — set + save + reload returns same value
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        mgr = _make_manager(config_path)
        mgr.set_refresh_interval_ms(interval)
        mgr.save()

        mgr2 = _make_manager(config_path)
        mgr2.load()

        assert mgr2.refresh_interval_ms() == interval


# ---------------------------------------------------------------------------
# Property 14: Out-of-range interval rejected
# Validates: Requirements 3.8
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    valid_interval=st.sampled_from(VALID_INTERVALS_MS),
    bad_interval=st.integers().filter(lambda x: x < 60000 or x > 1800000),
)
def test_property14_out_of_range_interval_rejected(
    valid_interval: int,
    bad_interval: int,
) -> None:
    # Feature: claude-usage-enhancements, Property 14: Out-of-range interval rejected — ValueError raised, previous value unchanged
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        mgr = _make_manager(config_path)
        mgr.set_refresh_interval_ms(valid_interval)

        with pytest.raises(ValueError):
            mgr.set_refresh_interval_ms(bad_interval)

        # Previous value is unchanged
        assert mgr.refresh_interval_ms() == valid_interval
