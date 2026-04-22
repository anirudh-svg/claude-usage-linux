"""Property-based tests for account_manager.py.

Feature: claude-usage-enhancements
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck
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


def _make_manager(config_path: Path) -> AccountManager:
    return AccountManager(config_path=config_path)


# ---------------------------------------------------------------------------
# Property 7: Account config round-trip
# Validates: Requirements 2.1, 2.2, 2.11
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
def test_property7_account_config_round_trip(
    entries: list[tuple[str, str]],
    active_index: int,
) -> None:
    # Feature: claude-usage-enhancements, Property 7: Account config round-trip
    active_index = active_index % len(entries)
    active_label = entries[active_index][0]

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"

        # Build and save
        mgr = _make_manager(config_path)
        for label, key in entries:
            mgr._accounts.append(Account(label=label, session_key=key))
        mgr._active_label = active_label
        mgr.save()

        # Reload into a fresh manager
        mgr2 = _make_manager(config_path)
        mgr2.load()

        # Verify identical account list
        assert [(a.label, a.session_key) for a in mgr2.accounts()] == entries
        # Verify active account
        assert mgr2.active_account() is not None
        assert mgr2.active_account().label == active_label


# ---------------------------------------------------------------------------
# Property 9: Switching active account updates state
# Validates: Requirements 2.4
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    entries=st.lists(
        st.tuples(label_strategy, key_strategy),
        min_size=2,
        max_size=10,
        unique_by=lambda t: t[0],
    ),
    target_index=st.integers(min_value=0, max_value=9),
)
def test_property9_switching_active_account(
    entries: list[tuple[str, str]],
    target_index: int,
) -> None:
    # Feature: claude-usage-enhancements, Property 9: Switching active account — set_active(label) results in active_account().label == label
    target_index = target_index % len(entries)
    target_label = entries[target_index][0]

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        mgr = _make_manager(config_path)
        for label, key in entries:
            mgr._accounts.append(Account(label=label, session_key=key))
        mgr._active_label = entries[0][0]
        mgr.save()

        mgr.set_active(target_label)

        assert mgr.active_account() is not None
        assert mgr.active_account().label == target_label


# ---------------------------------------------------------------------------
# Property 10: Adding an account persists and becomes active
# Validates: Requirements 2.7
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    initial_entries=st.lists(
        st.tuples(label_strategy, key_strategy),
        min_size=0,
        max_size=5,
        unique_by=lambda t: t[0],
    ),
    new_label=label_strategy,
    new_key=key_strategy,
)
def test_property10_add_account_persists_and_becomes_active(
    initial_entries: list[tuple[str, str]],
    new_label: str,
    new_key: str,
) -> None:
    # Feature: claude-usage-enhancements, Property 10: Adding an account persists and becomes active — add_account(label, key) → account in list, is active
    if any(label == new_label for label, _ in initial_entries):
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        mgr = _make_manager(config_path)
        for label, key in initial_entries:
            mgr._accounts.append(Account(label=label, session_key=key))
        if initial_entries:
            mgr._active_label = initial_entries[0][0]
        mgr.save()

        mgr.add_account(new_label, new_key)

        # Account is in the list with correct key
        labels = [a.label for a in mgr.accounts()]
        assert new_label in labels
        added = next(a for a in mgr.accounts() if a.label == new_label)
        assert added.session_key == new_key

        # Account is now active
        assert mgr.active_account() is not None
        assert mgr.active_account().label == new_label

        # Persisted: reload and verify
        mgr2 = _make_manager(config_path)
        mgr2.load()
        assert any(a.label == new_label and a.session_key == new_key for a in mgr2.accounts())
        assert mgr2.active_account().label == new_label


# ---------------------------------------------------------------------------
# Property 11: Removing an account removes it from config
# Validates: Requirements 2.8
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    entries=st.lists(
        st.tuples(label_strategy, key_strategy),
        min_size=2,
        max_size=10,
        unique_by=lambda t: t[0],
    ),
    remove_index=st.integers(min_value=0, max_value=9),
)
def test_property11_removing_account_removes_from_config(
    entries: list[tuple[str, str]],
    remove_index: int,
) -> None:
    # Feature: claude-usage-enhancements, Property 11: Removing an account removes it from config — remove_account on list with 2+ entries
    remove_index = remove_index % len(entries)
    remove_label = entries[remove_index][0]

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        mgr = _make_manager(config_path)
        for label, key in entries:
            mgr._accounts.append(Account(label=label, session_key=key))
        mgr._active_label = entries[0][0]
        mgr.save()

        mgr.remove_account(remove_label)

        # Not in in-memory list
        assert all(a.label != remove_label for a in mgr.accounts())

        # Not in persisted config
        mgr2 = _make_manager(config_path)
        mgr2.load()
        assert all(a.label != remove_label for a in mgr2.accounts())


# ---------------------------------------------------------------------------
# Property 12: Cannot remove the last account
# Validates: Requirements 2.9
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    label=label_strategy,
    key=key_strategy,
)
def test_property12_cannot_remove_last_account(
    label: str,
    key: str,
) -> None:
    # Feature: claude-usage-enhancements, Property 12: Cannot remove last account — remove_account on single-account manager raises ValueError
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        mgr = _make_manager(config_path)
        mgr._accounts.append(Account(label=label, session_key=key))
        mgr._active_label = label
        mgr.save()

        with pytest.raises(ValueError):
            mgr.remove_account(label)

        # Account list is unchanged
        assert len(mgr.accounts()) == 1
        assert mgr.accounts()[0].label == label
