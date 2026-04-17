#!/usr/bin/env python3
import sys

try:
    import gi
except ModuleNotFoundError:
    sys.exit(
        "Error: 'gi' (PyGObject) not found.\n"
        "This app requires the system Python, not a virtualenv.\n"
        "Run with:  /usr/bin/python3 main.py\n"
        "Or install system deps:  sudo apt install python3-gi gir1.2-appindicator3-0.1"
    )

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from tray_app import TrayApp


def main():
    app = TrayApp()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
