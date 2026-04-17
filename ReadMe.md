# Claude Usage Monitor for Linux

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A lightweight Ubuntu system tray app that shows your Claude.ai message usage — like a battery icon for your Claude quota.

## Features
- System tray icon showing current usage percentage (e.g. `C 42%`)
- Click the icon to see messages used, limit, and time until reset
- Auto-refreshes every 5 minutes
- Desktop notification at 80% and 90% usage
- Auto-starts on login

## Requirements
- Ubuntu 20.04+ (or any GNOME-based distro with AppIndicator support)
- Google Chrome / Chromium — and you must be **logged in to claude.ai** in Chrome

## Installation

```bash
git clone https://github.com/hari-kris/claude-usage-linux.git
cd claude-usage-linux
bash install.sh
```

Then start it immediately:

```bash
python3 main.py &
```

## How it works
1. At startup the app reads your `sessionKey` cookie directly from Chrome's local cookie store — no passwords are sent anywhere.
2. It calls the Claude.ai internal API to fetch your usage data.
3. Usage is displayed in the system tray and refreshed every 5 minutes.

## Manual session key override
If cookie extraction fails, create a file with your session key:

```bash
mkdir -p ~/.config/claude-usage-linux
# Paste your sessionKey value (from Chrome DevTools → Application → Cookies → claude.ai)
echo "sk-ant-..." > ~/.config/claude-usage-linux/session_key
```

## Finding the usage endpoint (advanced)
Claude.ai's internal API is undocumented. If usage data shows as "unavailable":

1. Open Chrome DevTools (F12) → Network tab
2. Navigate to claude.ai
3. Filter requests by `api/`
4. Look for a response that contains `messages_used`, `usage`, or `rate_limit`
5. Update `ORGS_ENDPOINT` or `BOOTSTRAP_ENDPOINT` in `claude_client.py` accordingly

## Uninstall

```bash
rm ~/.config/autostart/claude-usage-monitor.desktop
```

## License

[MIT](LICENSE) © 2026 Harinath
