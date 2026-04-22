"""Notifier — desktop notification wrapper with threshold and ETA alert tracking."""

from __future__ import annotations

from gi.repository import Notify

WARN_THRESHOLD = 80
CRITICAL_THRESHOLD = 90


class Notifier:
    """Wraps libnotify and tracks which alerts have fired for the current window period."""

    def __init__(self) -> None:
        # Threshold tracking (mirrors existing TrayApp._last_notified_threshold logic)
        self._last_notified_threshold: int = 0

        # ETA alert flags — reset each window period
        self._eta_warn_sent: bool = False
        self._eta_critical_sent: bool = False

    def notify_threshold(self, pct: float) -> None:
        """Fire warn/critical threshold notifications (extracted from TrayApp._maybe_notify)."""
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

    def notify_eta(self, eta_minutes: float) -> None:
        """Fire predictive ETA notification if not already sent for this window period.

        Sends a critical-urgency notification when eta_minutes <= 30,
        and a normal-urgency notification when eta_minutes <= 60.
        Each alert fires at most once per window period.
        """
        if eta_minutes <= 30 and not self._eta_critical_sent:
            self._eta_critical_sent = True
            self._eta_warn_sent = True  # critical implies warn already covered
            n = Notify.Notification.new(
                "Claude Usage — Limit Soon",
                f"At current rate, you'll hit your limit in ~{int(eta_minutes)} min.",
                "dialog-warning",
            )
            n.set_urgency(Notify.Urgency.CRITICAL)
            n.show()
        elif eta_minutes <= 60 and not self._eta_warn_sent:
            self._eta_warn_sent = True
            n = Notify.Notification.new(
                "Claude Usage — ETA Warning",
                f"At current rate, you'll hit your limit in ~{int(eta_minutes)} min.",
                "dialog-information",
            )
            n.show()

    def reset_predictive_state(self) -> None:
        """Clear ETA alert flags (called when the usage window resets)."""
        self._eta_warn_sent = False
        self._eta_critical_sent = False
