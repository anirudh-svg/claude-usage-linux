"""Property-based tests for predictor.py.

Feature: claude-usage-enhancements
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from predictor import Predictor, Sample


def _make_ts(base: datetime, offset_minutes: float) -> datetime:
    return base + timedelta(minutes=offset_minutes)


BASE_TS = datetime(2024, 1, 1, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Property 1: Consumption rate formula
# Validates: Requirements 1.2
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    pct1=st.floats(0, 99, allow_nan=False),
    pct2=st.floats(0, 100, allow_nan=False),
    elapsed=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False),
)
def test_property1_consumption_rate_formula(pct1: float, pct2: float, elapsed: float) -> None:
    # Feature: claude-usage-enhancements, Property 1: Consumption rate formula
    p = Predictor()
    t1 = BASE_TS
    t2 = _make_ts(t1, elapsed)
    p.add_sample(pct1, ts=t1)
    # Only add pct2 if it won't trigger a reset (pct2 >= pct1)
    if pct2 >= pct1:
        p.add_sample(pct2, ts=t2)
        expected = (pct2 - pct1) / elapsed
        result = p.consumption_rate()
        assert result is not None
        assert abs(result - expected) < 1e-9


# ---------------------------------------------------------------------------
# Property 2: ETA formula
# Validates: Requirements 1.3
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    pct=st.floats(0, 99, allow_nan=False),
    rate=st.floats(min_value=0.01, max_value=1000.0, allow_nan=False),
    elapsed=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False),
)
def test_property2_eta_formula(pct: float, rate: float, elapsed: float) -> None:
    # Feature: claude-usage-enhancements, Property 2: ETA formula
    # Build a predictor with two samples that produce the desired rate
    p = Predictor()
    t1 = BASE_TS
    t2 = _make_ts(t1, elapsed)
    pct1 = max(0.0, pct - rate * elapsed)
    pct2 = pct1 + rate * elapsed
    if pct2 > 100 or pct1 < 0:
        return  # skip invalid combinations
    p.add_sample(pct1, ts=t1)
    if pct2 >= pct1:
        p.add_sample(pct2, ts=t2)
    actual_rate = p.consumption_rate()
    if actual_rate is None or actual_rate <= 0:
        return
    current_pct = p._history[-1].pct
    if current_pct >= 100:
        return
    expected_eta = (100 - current_pct) / actual_rate
    result = p.eta_minutes()
    assert result is not None
    assert abs(result - expected_eta) < 1e-9


# ---------------------------------------------------------------------------
# Property 3: No ETA when rate is non-positive
# Validates: Requirements 1.6
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    pcts=st.lists(st.floats(0, 100, allow_nan=False), min_size=2, max_size=10),
)
def test_property3_no_eta_when_rate_nonpositive(pcts: list[float]) -> None:
    # Feature: claude-usage-enhancements, Property 3: No ETA when rate is non-positive
    # Build a non-increasing sequence so rate <= 0
    sorted_desc = sorted(pcts, reverse=True)
    p = Predictor()
    for i, pct in enumerate(sorted_desc):
        # Use add_sample carefully: a drop triggers reset, so feed monotone non-increasing
        # by resetting manually and re-adding
        pass

    # Simpler: directly test with two samples where pct2 <= pct1
    p2 = Predictor()
    t1 = BASE_TS
    t2 = _make_ts(t1, 5.0)
    high = max(pcts)
    low = min(pcts)
    p2.add_sample(high, ts=t1)
    # pct2 < pct1 triggers reset, so after reset only one sample — rate is None
    if low < high:
        p2.add_sample(low, ts=t2)
        # After reset, only one sample remains
        assert p2.consumption_rate() is None
        assert p2.eta_minutes() is None
    else:
        # pct2 == pct1: rate == 0
        p2.add_sample(high, ts=t2)
        rate = p2.consumption_rate()
        assert rate is not None and rate == 0.0
        assert p2.eta_minutes() is None


# ---------------------------------------------------------------------------
# Property 4: Predictor sample buffer is bounded
# Validates: Requirements 1.8
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    pcts=st.lists(st.floats(0, 100, allow_nan=False), min_size=31, max_size=200),
)
def test_property4_buffer_bounded(pcts: list[float]) -> None:
    # Feature: claude-usage-enhancements, Property 4: Predictor sample buffer is bounded
    p = Predictor()
    # Feed a monotonically non-decreasing sequence to avoid resets
    sorted_pcts = sorted(pcts)
    for i, pct in enumerate(sorted_pcts):
        ts = _make_ts(BASE_TS, float(i))
        p.add_sample(pct, ts=ts)
    assert len(p._history) <= Predictor.MAX_SAMPLES


# ---------------------------------------------------------------------------
# Property 6: Window reset clears predictor state
# Validates: Requirements 1.7
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    initial_pcts=st.lists(
        st.floats(10, 100, allow_nan=False), min_size=2, max_size=10
    ),
    drop=st.floats(min_value=0.1, max_value=9.9, allow_nan=False),
)
def test_property6_window_reset_clears_predictor(
    initial_pcts: list[float], drop: float
) -> None:
    # Feature: claude-usage-enhancements, Property 6: Window reset clears predictor and notifier state
    p = Predictor()
    sorted_pcts = sorted(initial_pcts)
    for i, pct in enumerate(sorted_pcts):
        ts = _make_ts(BASE_TS, float(i))
        p.add_sample(pct, ts=ts)

    # Ensure we have samples before the reset
    assert len(p._history) >= 1

    # Trigger a window reset: new pct is lower than the last recorded pct
    last_pct = p._history[-1].pct
    reset_pct = max(0.0, last_pct - drop)
    reset_ts = _make_ts(BASE_TS, float(len(sorted_pcts) + 1))
    p.add_sample(reset_pct, ts=reset_ts)

    # After reset, history should contain exactly 1 sample (the reset sample)
    assert len(p._history) == 1
    assert p._history[0].pct == reset_pct
