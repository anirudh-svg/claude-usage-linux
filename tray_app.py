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

from claude_client import ClaudeClient, UsageData, AuthError, FetchError
from account_manager import AccountManager
from settings_manager import SettingsManager
from predictor import Predictor
from notifier import Notifier
from session_key_dialog import SessionKeyDialog
import cookie_helper


class TrayApp:
    def __init__(self):
        Notify.init("Claude Usage Monitor")

        # ── Component instances ───────────────────────────────────────
        self._account_mgr = AccountManager()
        self._settings_mgr = SettingsManager()
        self._predictor = Predictor()
        self._notifier = Notifier()
        self._clients: dict[str, ClaudeClient] = {}
        self._timer_id: int | None = None
        self._auth_error: bool = False

        # ── Load persisted state ──────────────────────────────────────
        self._account_mgr.load()
        self._settings_mgr.load()

        # ── AppIndicator setup ────────────────────────────────────────
        self._indicator = AppIndicator.Indicator.new(
            "claude-usage-monitor",
            "dialog-information",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self._indicator.set_label("C …", "Claude Usage")

        # ── Placeholder menu item refs (populated by _rebuild_menu) ──
        self._header_item: Gtk.MenuItem
        self._5h_item: Gtk.MenuItem
        self._5h_reset_item: Gtk.MenuItem
        self._7d_item: Gtk.MenuItem
        self._7d_reset_item: Gtk.MenuItem
        self._fix_session_item: Gtk.MenuItem | None = None

        # ── Build initial menu ────────────────────────────────────────
        self._rebuild_menu()

        # ── First-run: open SessionKeyDialog if no accounts exist ─────
        if not self._account_mgr.accounts():
            GLib.idle_add(self._open_first_account_dialog)
        else:
            # Start polling immediately
            threading.Thread(target=self._fetch_and_update, daemon=True).start()

        # ── Start the recurring timer ─────────────────────────────────
        self._restart_timer()

    # ── Static helpers ────────────────────────────────────────────────

    def _static_item(self, text: str) -> Gtk.MenuItem:
        item = Gtk.MenuItem(label=text)
        item.set_sensitive(False)
        return item

    # ── Menu rebuild ─────────────────────────────────────────────────

    def _rebuild_menu(self) -> None:
        """Destroy and recreate the entire menu, then re-attach it to the indicator."""
        # Preserve any existing fix-session item state
        self._fix_session_item = None

        self._menu = Gtk.Menu()

        # Header + usage items
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

        # Accounts submenu
        accounts_item = Gtk.MenuItem(label="Accounts")
        accounts_item.set_submenu(self._build_accounts_submenu())
        self._menu.append(accounts_item)

        # Refresh Interval submenu
        interval_item = Gtk.MenuItem(label="Refresh Interval")
        interval_item.set_submenu(self._build_interval_submenu())
        self._menu.append(interval_item)

        # Set Session Key item (always visible)
        set_key_item = Gtk.MenuItem(label="Set Session Key")
        set_key_item.connect("activate", self._on_fix_session_key)
        self._menu.append(set_key_item)

        refresh_item = Gtk.MenuItem(label="Refresh")
        refresh_item.connect("activate", self._on_refresh)
        self._menu.append(refresh_item)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self._on_quit)
        self._menu.append(quit_item)

        self._menu.show_all()
        self._indicator.set_menu(self._menu)

    # ── Interval submenu ──────────────────────────────────────────────

    _INTERVAL_OPTIONS = [
        ("1 minute",  60000),
        ("5 minutes", 300000),
        ("15 minutes", 900000),
        ("30 minutes", 1800000),
    ]

    def _build_interval_submenu(self) -> Gtk.Menu:
        """Build and return the Refresh Interval submenu."""
        submenu = Gtk.Menu()
        current_ms = self._settings_mgr.refresh_interval_ms()
        first_item: Gtk.RadioMenuItem | None = None

        for label, ms in self._INTERVAL_OPTIONS:
            if first_item is None:
                item = Gtk.RadioMenuItem(label=label)
                first_item = item
            else:
                item = Gtk.RadioMenuItem.new_from_widget(first_item)
                item.set_label(label)
            if ms == current_ms:
                item.set_active(True)
            item.connect("toggled", self._on_interval_selected, ms)
            submenu.append(item)

        return submenu

    def _on_interval_selected(self, item: Gtk.RadioMenuItem, ms: int) -> None:
        """Handle toggled signal on a Refresh Interval RadioMenuItem."""
        if not item.get_active():
            return
        self._settings_mgr.set_refresh_interval_ms(ms)
        self._settings_mgr.save()
        self._restart_timer()

    # ── Accounts submenu ──────────────────────────────────────────────

    def _build_accounts_submenu(self) -> Gtk.Menu:
        """Build and return the Accounts submenu."""
        submenu = Gtk.Menu()
        active = self._account_mgr.active_account()
        active_label = active.label if active else None

        # One CheckMenuItem per account
        for account in self._account_mgr.accounts():
            item = Gtk.CheckMenuItem(label=account.label)
            item.set_active(account.label == active_label)
            item.connect("toggled", self._on_account_selected, account.label)
            submenu.append(item)

        submenu.append(Gtk.SeparatorMenuItem())

        # Remove Account submenu
        remove_item = Gtk.MenuItem(label="Remove Account")
        remove_submenu = self._build_remove_submenu()
        remove_item.set_submenu(remove_submenu)
        submenu.append(remove_item)

        # Add Account item
        add_item = Gtk.MenuItem(label="Add Account")
        add_item.connect("activate", self._on_add_account)
        submenu.append(add_item)

        return submenu

    def _build_remove_submenu(self) -> Gtk.Menu:
        """Build the Remove Account nested submenu."""
        submenu = Gtk.Menu()
        active = self._account_mgr.active_account()
        active_label = active.label if active else None
        accounts = self._account_mgr.accounts()

        non_active = [a for a in accounts if a.label != active_label]

        if len(accounts) <= 1:
            disabled = Gtk.MenuItem(label="Cannot remove last account")
            disabled.set_sensitive(False)
            submenu.append(disabled)
        else:
            for account in non_active:
                item = Gtk.MenuItem(label=account.label)
                item.connect("activate", self._on_remove_account, account.label)
                submenu.append(item)

        return submenu

    # ── Account event handlers ────────────────────────────────────────

    def _on_account_selected(self, item: Gtk.CheckMenuItem, label: str) -> None:
        """Handle toggled signal on an account CheckMenuItem."""
        if not item.get_active():
            return  # guard against re-entrancy (uncheck of previously active item)
        active = self._account_mgr.active_account()
        if active and active.label == label:
            return  # already active, nothing to do
        self._switch_account(label)
        self._rebuild_menu()

    def _on_add_account(self, _) -> None:
        """Open SessionKeyDialog with empty fields to add a new account."""
        dialog = SessionKeyDialog(parent=None, label="", session_key="")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            label = dialog.get_label() or "Account"
            key = dialog.get_session_key()
            self._account_mgr.add_account(label, key)
            self._switch_account(label)
            self._rebuild_menu()
        dialog.destroy()

    def _on_remove_account(self, _, label: str) -> None:
        """Remove the given account; show error dialog if it's the last one."""
        try:
            self._account_mgr.remove_account(label)
        except ValueError as exc:
            err_dialog = Gtk.MessageDialog(
                transient_for=None,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=str(exc),
            )
            err_dialog.run()
            err_dialog.destroy()
            return
        self._rebuild_menu()

    # ── First-run dialog ──────────────────────────────────────────────

    def _open_first_account_dialog(self) -> bool:
        """Open SessionKeyDialog to create the first account.

        Tries to seed the session key from the Chrome cookie fallback.
        Scheduled via GLib.idle_add so it runs after the GTK main loop starts.
        """
        seed_key = ""
        try:
            seed_key = cookie_helper.get_session_key()
        except Exception:
            pass

        dialog = SessionKeyDialog(parent=None, label="Personal", session_key=seed_key)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            label = dialog.get_label() or "Personal"
            key = dialog.get_session_key()
            self._account_mgr.add_account(label, key)
            threading.Thread(target=self._fetch_and_update, daemon=True).start()
        dialog.destroy()
        return False  # don't repeat

    # ── Timer management ──────────────────────────────────────────────

    def _restart_timer(self) -> None:
        """Cancel any existing timer and start a new one with the current interval."""
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        self._timer_id = GLib.timeout_add(
            self._settings_mgr.refresh_interval_ms(), self._schedule_refresh
        )

    # ── Client cache ──────────────────────────────────────────────────

    def _get_client(self) -> ClaudeClient:
        """Return a cached ClaudeClient for the active account, creating one on miss."""
        account = self._account_mgr.active_account()
        if account is None:
            raise RuntimeError("No active account configured.")
        if account.label not in self._clients:
            self._clients[account.label] = ClaudeClient(account.session_key)
        return self._clients[account.label]

    # ── Account switching ─────────────────────────────────────────────

    def _switch_account(self, label: str) -> None:
        """Switch the active account, reset predictor/notifier, and trigger a poll."""
        self._account_mgr.set_active(label)
        self._predictor = Predictor()
        self._notifier.reset_predictive_state()
        self._auth_error = False
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    # ── Polling ───────────────────────────────────────────────────────

    def _schedule_refresh(self) -> bool:
        """GLib timer callback — fires a background poll and reschedules itself."""
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
        return True  # keep the timer alive

    def _fetch_and_update(self) -> None:
        try:
            usage = self._get_client().fetch_usage()
            GLib.idle_add(self._update_menu, usage, None)
        except AuthError:
            account = self._account_mgr.active_account()
            if account:
                self._clients.pop(account.label, None)
            n = Notify.Notification.new(
                "Claude — Session Expired",
                "Session expired — click Fix Session Key in the tray",
                "dialog-warning",
            )
            n.show()
            GLib.idle_add(self._on_auth_error)
        except (FetchError, RuntimeError) as e:
            GLib.idle_add(self._update_menu, None, str(e))

    def _on_auth_error(self) -> bool:
        """Called on the GTK main thread after an AuthError."""
        self._auth_error = True
        self._update_menu(None, "Session expired — Fix Session Key below")
        return False

    # ── Menu update ───────────────────────────────────────────────────

    def _update_menu(self, usage: UsageData | None, error: str | None) -> None:
        # Remove any existing "Fix Session Key" item first
        if self._fix_session_item is not None:
            self._menu.remove(self._fix_session_item)
            self._fix_session_item = None

        if error:
            self._5h_item.set_label(f"⚠ {error[:70]}")
            self._5h_reset_item.set_label("")
            self._7d_item.set_label("")
            self._7d_reset_item.set_label("")
            self._indicator.set_label("C !", "Claude — error")

            if self._auth_error:
                self._insert_fix_session_item()

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

        # Threshold notifications
        if primary is not None:
            self._notifier.notify_threshold(primary)
            self._predictor.add_sample(primary)
            eta = self._predictor.eta_minutes()
            if eta is not None:
                self._notifier.notify_eta(eta)

        self._menu.show_all()

    def _insert_fix_session_item(self) -> None:
        """Insert a '⚠ Fix Session Key' menu item before the Refresh item."""
        item = Gtk.MenuItem(label="⚠ Fix Session Key")
        item.connect("activate", self._on_fix_session_key)
        # Insert before the second-to-last item (Refresh is at -2, Quit at -1)
        children = self._menu.get_children()
        # Find the Refresh item position
        insert_pos = len(children) - 2  # before Refresh
        self._menu.insert(item, insert_pos)
        self._fix_session_item = item

    def _on_fix_session_key(self, _) -> None:
        """Open SessionKeyDialog pre-populated with the active account."""
        account = self._account_mgr.active_account()
        label = account.label if account else ""
        key = account.session_key if account else ""
        dialog = SessionKeyDialog(parent=None, label=label, session_key=key)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_key = dialog.get_session_key()
            new_label = dialog.get_label()
            if account:
                self._account_mgr.update_session_key(account.label, new_key)
                # Invalidate cached client so it's recreated with the new key
                self._clients.pop(account.label, None)
            else:
                self._account_mgr.add_account(new_label, new_key)
            self._auth_error = False
            threading.Thread(target=self._fetch_and_update, daemon=True).start()
        dialog.destroy()

    # ── Menu event handlers ───────────────────────────────────────────

    def _on_refresh(self, _) -> None:
        self._5h_item.set_label("Refreshing…")
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _on_quit(self, _) -> None:
        Notify.uninit()
        Gtk.main_quit()
