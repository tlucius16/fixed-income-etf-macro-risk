"""Tests for src.data.options — pure logic."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.data.options import (
    _friday_dates_in_range,
)


# ---------------------------------------------------------------------------
# Friday date generation
# ---------------------------------------------------------------------------

class TestFridayDatesInRange:
    def test_single_friday(self):
        dates = _friday_dates_in_range("2024-11-01", "2024-11-01")
        assert len(dates) == 1
        assert dates[0].weekday() == 4  # Friday

    def test_first_friday_advances_correctly(self):
        # 2024-11-04 is a Monday; first Friday is 2024-11-08
        dates = _friday_dates_in_range("2024-11-04", "2024-11-20")
        assert dates[0].weekday() == 4
        assert str(dates[0]) == "2024-11-08"

    def test_weekly_cadence(self):
        dates = _friday_dates_in_range("2024-01-05", "2024-03-01")
        diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        assert all(d == 7 for d in diffs)

    def test_empty_range_returns_empty(self):
        # end before any Friday
        dates = _friday_dates_in_range("2024-11-11", "2024-11-13")
        assert dates == []

    def test_start_on_friday_includes_it(self):
        dates = _friday_dates_in_range("2024-11-08", "2024-11-08")
        from datetime import date
        assert dates == [date(2024, 11, 8)]
