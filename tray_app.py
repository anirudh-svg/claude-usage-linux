import threading
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')

try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3 as AppIndicator
except ValueError:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as AppIndicator

from gi.repository import Gtk, GLib, Notify

from cookie_helper import get_session_key
from claude_client import ClaudeClient, UsageData, AuthError, FetchError

REFRESH_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes
WARN_THRESHOLD = 80
CRITICAL_THRESHOLD = 90


class TrayApp:
    def __init__(self):
        Notify.init("Claude Usage Monitor")

        self._indicator = AppIndicator.Indicator.new(
            "claude-usage-monitor",
            "dialog-information",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self._indicator.set_label("C …", "Claude Usage")

        self._menu = Gtk.Menu()

        self._header_item = self._static_item("Claude Usage")
        self._5h_item = self._static_item("Loading…")
        self._5h_reset_item = self._static_item("")
        self._7d_item = self._static_item("")
        self._7d_reset_item = self._static_item("")

        for item in (
            self._header_item,
            Gtk.SeparatorMenuItem(),
            self._5h_item,
            self._5h_reset_item,
            Gtk.SeparatorMenuItem(),
            self._7d_item,
            self._7d_reset_item,
            Gtk.SeparatorMenuItem(),
        ):
            self._menu.append(item)

        refresh_item = Gtk.MenuItem(label="Refresh")
        refresh_item.connect("activate", self._on_refresh)
        self._menu.append(refresh_item)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._on_quit)
        self._menu.append(quit_item)

        self._menu.show_all()
        self._indicator.set_menu(self._menu)

        self._last_notified_threshold = 0
        self._client: ClaudeClient | None = None

        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        GLib.timeout_add(REFRESH_INTERVAL_MS, self._schedule_refresh)

    def _static_item(self, text: str) -> Gtk.MenuItem:
        item = Gtk.MenuItem(label=text)
        item.set_sensitive(False)
        return item

    def _get_client(self) -> ClaudeClient:
        if self._client is None:
            key = get_session_key()
            self._client = ClaudeClient(key)
        return self._client

    def _fetch_and_update(self):
        try:
            usage = self._get_client().fetch_usage()
            GLib.idle_add(self._update_menu, usage, None)
        except AuthError as e:
            self._client = None
            GLib.idle_add(self._update_menu, None, str(e))
        except (FetchError, RuntimeError) as e:
            GLib.idle_add(self._update_menu, None, str(e))

    def _update_menu(self, usage: UsageData | None, error: str | None):
        if error:
            self._5h_item.set_label(f"⚠ {error[:70]}")
            self._5h_reset_item.set_label("")
            self._7d_item.set_label("")
            self._7d_reset_item.set_label("")
            self._indicator.set_label("C !", "Claude — error")
            self._menu.show_all()
            return

        # 5-hour window
        if usage.five_hour_pct is not None:
            pct_5h = int(usage.five_hour_pct)
            self._5h_item.set_label(f"5-hour window: {pct_5h}% used")
            reset = usage.five_hour_reset_str
            self._5h_reset_item.set_label(f"  ↻ Resets in {reset}" if reset else "")
        else:
            self._5h_item.set_label("5-hour window: —")
            self._5h_reset_item.set_label("")

        # 7-day window
        if usage.seven_day_pct is not None:
            pct_7d = int(usage.seven_day_pct)
            self._7d_item.set_label(f"7-day window:  {pct_7d}% used")
            reset7 = usage.seven_day_reset_str
            self._7d_reset_item.set_label(f"  ↻ Resets in {reset7}" if reset7 else "")
        else:
            self._7d_item.set_label("7-day window:  —")
            self._7d_reset_item.set_label("")

        # Tray label: show worst-case utilization
        primary = usage.primary_pct
        label = f"C {int(primary)}%" if primary is not None else "C"
        self._indicator.set_label(label, "Claude Usage")
        self._menu.show_all()

        if primary is not None:
            self._maybe_notify(primary)

    def _maybe_notify(self, pct: float):
        if pct >= CRITICAL_THRESHOLD and self._last_notified_threshold < CRITICAL_THRESHOLD:
            self._last_notified_threshold = CRITICAL_THRESHOLD
            n = Notify.Notification.new(
                "Claude Usage — Critical",
                f"At {int(pct)}% of your limit — you may be rate-limited soon.",
                "dialog-warning",
            )
            n.set_urgency(Notify.Urgency.CRITICAL)
            n.show()
        elif pct >= WARN_THRESHOLD and self._last_notified_threshold < WARN_THRESHOLD:
            self._last_notified_threshold = WARN_THRESHOLD
            n = Notify.Notification.new(
                "Claude Usage Warning",
                f"At {int(pct)}% of your message limit.",
                "dialog-information",
            )
            n.show()
        elif pct < WARN_THRESHOLD:
            self._last_notified_threshold = 0

    def _schedule_refresh(self) -> bool:
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        return True

    def _on_refresh(self, _):
        self._5h_item.set_label("Refreshing…")
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _on_quit(self, _):
        Notify.uninit()
        Gtk.main_quit()
