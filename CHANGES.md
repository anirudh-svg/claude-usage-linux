# Changes

## New features

### Predictive notifications

The app now tracks usage rate over time and estimates when you will hit your limit. A warning notification fires when the estimated time remaining drops to 60 minutes, and a critical notification fires at 30 minutes. These alerts fire at most once per usage window period and reset automatically when the window resets.

New file: `predictor.py` — rolling sample history, consumption rate calculation, ETA computation.
New file: `notifier.py` — notification logic extracted from `tray_app.py`, extended with ETA-based alerts.

### Multiple account support

You can now configure more than one Claude account and switch between them from the tray menu. An Accounts submenu lists all configured accounts, with the active one marked. From the submenu you can add a new account or remove an existing one.

Account data is stored in `~/.config/claude-usage-linux/config.json`.

New file: `account_manager.py` — account storage, loading, saving, and switching.

### Configurable refresh interval

A Refresh Interval submenu in the tray lets you choose how often the app polls for usage data. The available options are 1 minute, 5 minutes, 15 minutes, and 30 minutes. The selection takes effect immediately without restarting the app and is saved across sessions.

New file: `settings_manager.py` — interval persistence in `config.json`.

### In-app session key dialog

A Set Session Key menu item is always available in the tray. Clicking it opens a dialog where you can enter or update the session key for the active account. The key field is masked by default with a toggle to reveal it. If the session key field is left empty, the dialog shows a validation message and stays open.

When a session expires during polling, a Fix Session Key item appears in the tray menu as a shortcut to the same dialog.

New file: `session_key_dialog.py` — GTK3 dialog for account name and session key entry.

## Modified files

### tray_app.py

Refactored to use the new components. The hardcoded refresh interval, warn threshold, and critical threshold constants have been removed. The polling timer is now cancellable and restarts when the interval is changed. The `_maybe_notify` method has been removed in favour of the `Notifier` class. On startup, if no accounts are configured, the session key dialog opens automatically.

### cookie_helper.py

Simplified. The `save_manual_session_key` function has been removed as it is no longer needed. The Chrome cookie extraction and legacy session key file fallback are kept as a convenience for seeding the first-run dialog.

## New files summary

| File | Purpose |
|---|---|
| `predictor.py` | Usage rate tracking and ETA calculation |
| `notifier.py` | Desktop notification logic |
| `account_manager.py` | Multi-account storage and management |
| `settings_manager.py` | User preference persistence |
| `session_key_dialog.py` | GTK3 dialog for session key entry |

## Configuration file

All persistent state is stored in `~/.config/claude-usage-linux/config.json`. The format is:

```json
{
  "accounts": [
    { "label": "Personal", "session_key": "sk-ant-..." }
  ],
  "active_account": "Personal",
  "settings": {
    "refresh_interval_ms": 300000
  }
}
```

The legacy `~/.config/claude-usage-linux/session_key` file is still read as a fallback on first run.
