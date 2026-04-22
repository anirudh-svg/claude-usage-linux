"""SessionKeyDialog — GTK3 dialog for adding or editing a Claude account."""

from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class SessionKeyDialog(Gtk.Dialog):
    """Dialog for entering or editing an account label and session key.

    Usage::

        dialog = SessionKeyDialog(parent, label="Personal", session_key="sk-ant-...")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            label = dialog.get_label()
            key = dialog.get_session_key()
        dialog.destroy()
    """

    def __init__(self, parent, label: str = "", session_key: str = "") -> None:
        super().__init__(title="Add / Edit Account", transient_for=parent, modal=True)
        self.set_default_size(420, -1)
        self.set_border_width(12)

        # ── Content area ──────────────────────────────────────────────
        content = self.get_content_area()
        content.set_spacing(8)

        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(12)
        grid.set_margin_top(4)
        grid.set_margin_bottom(8)
        content.add(grid)

        # Row 0 — Account name
        name_label = Gtk.Label(label="Account name", xalign=0.0)
        grid.attach(name_label, 0, 0, 1, 1)

        self._label_entry = Gtk.Entry()
        self._label_entry.set_hexpand(True)
        self._label_entry.set_text(label)
        grid.attach(self._label_entry, 1, 0, 2, 1)

        # Row 1 — Session key
        key_label = Gtk.Label(label="Session key", xalign=0.0)
        grid.attach(key_label, 0, 1, 1, 1)

        self._key_entry = Gtk.Entry()
        self._key_entry.set_hexpand(True)
        self._key_entry.set_visibility(False)  # password-style by default
        self._key_entry.set_text(session_key)
        grid.attach(self._key_entry, 1, 1, 1, 1)

        self._toggle_btn = Gtk.Button(label="Show")
        self._toggle_btn.connect("clicked", self._on_toggle_visibility)
        grid.attach(self._toggle_btn, 2, 1, 1, 1)

        # Row 2 — Inline validation message (hidden by default)
        self._validation_label = Gtk.Label(label="Session key cannot be empty", xalign=0.0)
        self._validation_label.set_no_show_all(True)
        # Apply red colour via CSS
        css = b"label { color: red; }"
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        self._validation_label.get_style_context().add_provider(
            provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        grid.attach(self._validation_label, 1, 2, 2, 1)

        # ── Action buttons ────────────────────────────────────────────
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        save_btn = self.add_button("Save", Gtk.ResponseType.OK)
        save_btn.get_style_context().add_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)

        # Intercept the response signal to validate before closing
        self.connect("response", self._on_response)

        content.show_all()
        self._validation_label.hide()

    # ── Private helpers ───────────────────────────────────────────────

    def _on_toggle_visibility(self, _btn: Gtk.Button) -> None:
        visible = self._key_entry.get_visibility()
        self._key_entry.set_visibility(not visible)
        self._toggle_btn.set_label("Hide" if not visible else "Show")

    def _on_response(self, _dialog, response_id: int) -> None:
        """Intercept Save to run validation; stop the dialog from closing if invalid."""
        if response_id != Gtk.ResponseType.OK:
            return
        if not self._key_entry.get_text().strip():
            self._validation_label.show()
            # Prevent the dialog from closing by stopping signal emission
            self.stop_emission_by_name("response")

    # ── Public API ────────────────────────────────────────────────────

    def get_label(self) -> str:
        """Return the current value of the account name field."""
        return self._label_entry.get_text()

    def get_session_key(self) -> str:
        """Return the current value of the session key field."""
        return self._key_entry.get_text()
