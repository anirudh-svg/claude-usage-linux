# Implementation Plan: Claude Usage Enhancements

## Overview

Implement four enhancements to the Claude Usage Monitor GTK3 tray app: predictive rate-based notifications, multiple account support, custom refresh interval, and an in-app session key dialog. New components are added as separate modules and wired into a refactored `TrayApp`.

## Tasks

- [x] 1. Create `predictor.py` — Predictor and Sample classes
  - Define `Sample` dataclass with `ts: datetime` and `pct: float` fields
  - Implement `Predictor` with `MAX_SAMPLES = 30` bounded deque history
  - Implement `add_sample(pct, ts=None)` — appends sample, detects window reset (pct < previous pct), calls `reset()` on reset
  - Implement `consumption_rate()` — returns `(pct_newest - pct_oldest) / elapsed_minutes` or `None` if fewer than 2 samples
  - Implement `eta_minutes()` — returns `(100 - current_pct) / rate` or `None` if rate <= 0 or pct >= 100
  - Implement `reset()` — clears deque
  - _Requirements: 1.1, 1.2, 1.3, 1.6, 1.7, 1.8_

  - [ ]* 1.1 Write property test for consumption rate formula (Property 1)
    - **Property 1: Consumption rate formula**
    - **Validates: Requirements 1.2**

  - [ ]* 1.2 Write property test for ETA formula (Property 2)
    - **Property 2: ETA formula**
    - **Validates: Requirements 1.3**

  - [ ]* 1.3 Write property test for no ETA when rate is non-positive (Property 3)
    - **Property 3: No ETA when rate is non-positive**
    - **Validates: Requirements 1.6**

  - [ ]* 1.4 Write property test for bounded sample buffer (Property 4)
    - **Property 4: Predictor sample buffer is bounded**
    - **Validates: Requirements 1.8**

  - [ ]* 1.5 Write property test for window reset clears state (Property 6)
    - **Property 6: Window reset clears predictor and notifier state**
    - **Validates: Requirements 1.7**

- [x] 2. Create `notifier.py` — Notifier class
  - Extract existing `_maybe_notify` threshold logic from `TrayApp` into `Notifier.notify_threshold(pct)`
  - Implement `notify_eta(eta_minutes)` — fires warn notification at <= 60 min, critical at <= 30 min; tracks `_eta_warn_sent` and `_eta_critical_sent` flags per window period
  - Implement `reset_predictive_state()` — clears ETA alert flags
  - _Requirements: 1.4, 1.5, 1.6, 1.7_

  - [ ]* 2.1 Write property test for ETA notification thresholds (Property 5)
    - **Property 5: ETA notification fires at correct thresholds**
    - **Validates: Requirements 1.4, 1.5**

- [x] 3. Create `account_manager.py` — Account dataclass and AccountManager
  - Define `Account` dataclass with `label: str` and `session_key: str`
  - Implement `AccountManager` reading/writing `~/.config/claude-usage-linux/config.json` under the `accounts` and `active_account` keys
  - Implement `load()`, `save()`, `accounts()`, `active_account()`, `set_active(label)`
  - Implement `add_account(label, session_key) -> Account` — appends and saves
  - Implement `remove_account(label)` — raises `ValueError("At least one account must remain")` if last account; saves on success
  - Implement `update_session_key(label, session_key)` — updates in-place and saves
  - Handle missing/corrupt config file gracefully (treat as empty, open dialog in TrayApp)
  - _Requirements: 2.1, 2.2, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12_

  - [ ]* 3.1 Write property test for account config round-trip (Property 7)
    - **Property 7: Account config round-trip**
    - **Validates: Requirements 2.1, 2.2, 2.11**

  - [ ]* 3.2 Write property test for switching active account (Property 9)
    - **Property 9: Switching active account updates state**
    - **Validates: Requirements 2.4**

  - [ ]* 3.3 Write property test for add account persists and becomes active (Property 10)
    - **Property 10: Adding an account persists and becomes active**
    - **Validates: Requirements 2.7**

  - [ ]* 3.4 Write property test for remove account (Property 11)
    - **Property 11: Removing an account removes it from config**
    - **Validates: Requirements 2.8**

  - [ ]* 3.5 Write property test for cannot remove last account (Property 12)
    - **Property 12: Cannot remove the last account**
    - **Validates: Requirements 2.9**

- [x] 4. Create `settings_manager.py` — SettingsManager
  - Define `VALID_INTERVALS_MS = [60000, 300000, 900000, 1800000]` and `DEFAULT_INTERVAL_MS = 300000`
  - Implement `SettingsManager` reading/writing `config.json` under the `settings` key
  - Implement `load()`, `save()`, `refresh_interval_ms() -> int`, `set_refresh_interval_ms(ms)` — raises `ValueError` for values outside `[60000, 1800000]`
  - Default to `DEFAULT_INTERVAL_MS` when key is absent from config
  - _Requirements: 3.1, 3.2, 3.3, 3.7, 3.8_

  - [ ]* 4.1 Write property test for refresh interval round-trip (Property 13)
    - **Property 13: Refresh interval round-trip**
    - **Validates: Requirements 3.1, 3.2, 3.7**

  - [ ]* 4.2 Write property test for out-of-range interval rejected (Property 14)
    - **Property 14: Out-of-range interval is rejected**
    - **Validates: Requirements 3.8**

- [x] 5. Create `session_key_dialog.py` — SessionKeyDialog GTK widget
  - Implement `SessionKeyDialog(Gtk.Dialog)` with `__init__(parent, label="", session_key="")`
  - Add labeled `Gtk.Entry` for account name and password-style `Gtk.Entry` for session key
  - Add "Show/Hide" toggle button that flips `entry.set_visibility()`; key field starts with `visibility=False`
  - Add inline red validation `Gtk.Label` (hidden by default); show it when Save is clicked with empty key
  - Add "Save" (`Gtk.ResponseType.OK`) and "Cancel" (`Gtk.ResponseType.CANCEL`) buttons
  - Pre-populate fields from constructor args
  - Implement `get_label() -> str` and `get_session_key() -> str`
  - _Requirements: 4.1, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.10_

  - [ ]* 5.1 Write property test for dialog pre-populates from existing account (Property 16)
    - **Property 16: Dialog pre-populates from existing account**
    - **Validates: Requirements 4.4**

  - [ ]* 5.2 Write property test for Save with empty key rejected (Property 18)
    - **Property 18: Save with empty key is rejected with validation message**
    - **Validates: Requirements 4.7**

  - [ ]* 5.3 Write property test for Cancel leaves account state unchanged (Property 19)
    - **Property 19: Cancel leaves account state unchanged**
    - **Validates: Requirements 4.8**

  - [ ]* 5.4 Write property test for session key visibility toggle (Property 20)
    - **Property 20: Session key field visibility toggle**
    - **Validates: Requirements 4.10**

- [x] 6. Checkpoint — Ensure all component tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Refactor `tray_app.py` — integrate all new components
  - Replace module-level `REFRESH_INTERVAL_MS` constant with `SettingsManager`-driven value
  - Add `self._account_mgr`, `self._settings_mgr`, `self._predictor`, `self._notifier`, `self._clients`, `self._timer_id` instance attributes
  - On startup: call `account_mgr.load()` and `settings_mgr.load()`; if no accounts exist open `SessionKeyDialog` to create the first account
  - Replace hardcoded `GLib.timeout_add` with a cancellable timer helper that uses `GLib.timeout_add` / `GLib.source_remove` and restarts when interval changes
  - Remove `_maybe_notify` — delegate to `self._notifier.notify_threshold()` and `self._notifier.notify_eta()`
  - After each successful poll, call `self._predictor.add_sample(primary_pct)` and `self._notifier.notify_eta(self._predictor.eta_minutes())`
  - On `AuthError`: clear cached client, show tray notification, add highlighted "Fix Session Key" menu item that opens `SessionKeyDialog`
  - _Requirements: 1.4, 1.5, 1.7, 2.4, 2.12, 3.5, 4.2, 4.9_

- [x] 8. Build Accounts submenu in `tray_app.py`
  - Add `_build_accounts_submenu()` method that creates a `Gtk.Menu` with one `Gtk.CheckMenuItem` per account
  - Mark the active account's item with `set_active(True)`; connect each item's `toggled` signal to `_on_account_selected`
  - Add "Add Account" `Gtk.MenuItem` at the bottom of the submenu; connect to handler that opens `SessionKeyDialog` with empty fields
  - Add "Remove Account" submenu or per-account remove items; show GTK error dialog if last account removal is attempted
  - Attach submenu to a top-level "Accounts" menu item; call `_rebuild_menu()` after any account change
  - _Requirements: 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9_

  - [ ]* 8.1 Write property test for account submenu reflects account list (Property 8)
    - **Property 8: Account submenu reflects account list**
    - **Validates: Requirements 2.3, 2.5**

- [x] 9. Build Refresh Interval submenu in `tray_app.py`
  - Add `_build_interval_submenu()` method that creates a `Gtk.Menu` with four `Gtk.RadioMenuItem` entries: 1 min, 5 min, 15 min, 30 min
  - Mark the currently active interval's item; connect each item's `toggled` signal to `_on_interval_selected`
  - In `_on_interval_selected`: call `settings_mgr.set_refresh_interval_ms(ms)`, restart the polling timer with the new interval
  - Attach submenu to a top-level "Refresh Interval" menu item
  - _Requirements: 3.4, 3.5, 3.6, 3.7_

  - [ ]* 9.1 Write property test for interval submenu reflects current selection (Property 15)
    - **Property 15: Interval submenu reflects current selection**
    - **Validates: Requirements 3.4, 3.6**

- [x] 10. Add "Set Session Key" menu item and wire `SessionKeyDialog` for existing accounts
  - Add "Set Session Key" item to the tray menu (or active account submenu)
  - Connect to handler that opens `SessionKeyDialog` pre-populated with active account's label and key
  - On Save: call `account_mgr.update_session_key(label, key)`, invalidate cached client, trigger immediate poll
  - On Cancel: no-op
  - _Requirements: 4.1, 4.2, 4.4, 4.6, 4.8_

  - [ ]* 10.1 Write property test for Save with non-empty key persists the new key (Property 17)
    - **Property 17: Save with non-empty key persists the new key**
    - **Validates: Requirements 4.6**

- [x] 11. Create `tests/test_unit.py` — unit tests for startup and structural behavior
  - Test startup with absent config: `AccountManager.load()` returns empty list, `TrayApp` opens `SessionKeyDialog`
  - Test startup with valid config: active account is loaded correctly
  - Test `SessionKeyDialog` structure: label entry, key entry, Save button, Cancel button all present
  - Test "Add Account" path: `SessionKeyDialog` opens with empty fields
  - Test `AccountManager` capacity: 10 accounts can be added and all retrieved via `accounts()`
  - Test Refresh Interval submenu: exactly 4 options displayed
  - Test AuthError path: "Fix Session Key" item appears in menu after auth failure
  - _Requirements: 2.10, 2.12, 3.4, 4.3, 4.5, 4.9_

- [x] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Simplify `cookie_helper.py` now that `SessionKeyDialog` handles manual key entry
  - Remove or deprecate `save_manual_session_key` if it is no longer called by any code path
  - Keep `_extract_from_chrome()` and `_read_manual_session_key()` as fallback for users who have an existing session key file; `get_session_key()` is now only used as a last-resort fallback when `AccountManager` has no accounts
  - _Requirements: 4.1, 4.2_

- [x] 14. Cleanup — delete `.kiro/specs/` directory from the repository
  - Remove the entire `.kiro/specs/` directory tree from the repo
  - _This is a post-implementation housekeeping step requested by the user_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests use Hypothesis with `@settings(max_examples=100)`; each test includes a comment: `# Feature: claude-usage-enhancements, Property N: <property_text>`
- Unit tests use pytest and do not require a running GTK display (use `Gtk.init_check` or mock where needed)
