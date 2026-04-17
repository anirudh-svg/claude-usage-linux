#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/claude-usage-monitor.desktop"

echo "==> Installing system dependencies..."
sudo apt install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-notify-0.7 \
    gir1.2-appindicator3-0.1 \
    libnotify-bin \
    python3-pip

echo "==> Installing Python dependencies (system Python)..."
# Must use system pip3, not a virtualenv, because gi/AppIndicator are system packages
/usr/bin/pip3 install --user -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null \
    || /usr/bin/python3 -m pip install --user -r "$SCRIPT_DIR/requirements.txt"

echo "==> Setting up autostart entry..."
mkdir -p "$AUTOSTART_DIR"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Claude Usage Monitor
Comment=Show Claude.ai usage in the system tray
Exec=/usr/bin/python3 $SCRIPT_DIR/main.py
Icon=dialog-information
X-GNOME-Autostart-enabled=true
EOF

echo ""
echo "Done! To start the app now, run:"
echo "  /usr/bin/python3 $SCRIPT_DIR/main.py &"
echo ""
echo "NOTE: Always use /usr/bin/python3 (system Python), not a virtualenv."
echo "      The 'gi' (PyGObject) library is a system package and is not"
echo "      available inside virtualenvs unless created with --system-site-packages."
echo ""
echo "It will also auto-start on your next login."
