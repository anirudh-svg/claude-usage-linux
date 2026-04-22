"""Predictor — rolling consumption rate and ETA computation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Sample:
    ts: datetime   # UTC timestamp of the poll
    pct: float     # primary_pct value (0–100)


class Predictor:
    MAX_SAMPLES = 30

    def __init__(self) -> None:
        self._history: deque[Sample] = deque(maxlen=self.MAX_SAMPLES)

    def add_sample(self, pct: float, ts: datetime | None = None) -> None:
        """Append a sample; detect window reset (pct < previous pct) and call reset()."""
        if ts is None:
            ts = datetime.now(tz=timezone.utc)
        if self._history and pct < self._history[-1].pct:
            self.reset()
        self._history.append(Sample(ts=ts, pct=pct))

    def consumption_rate(self) -> float | None:
        """Return pct/min or None if fewer than 2 samples."""
        if len(self._history) < 2:
            return None
        oldest = self._history[0]
        newest = self._history[-1]
        elapsed_minutes = (newest.ts - oldest.ts).total_seconds() / 60
        if elapsed_minutes <= 0:
            return None
        return (newest.pct - oldest.pct) / elapsed_minutes

    def eta_minutes(self) -> float | None:
        """Return minutes to 100% or None if rate <= 0 or pct >= 100."""
        rate = self.consumption_rate()
        if rate is None or rate <= 0:
            return None
        current_pct = self._history[-1].pct
        if current_pct >= 100:
            return None
        return (100 - current_pct) / rate

    def reset(self) -> None:
        """Clear sample history."""
        self._history.clear()
