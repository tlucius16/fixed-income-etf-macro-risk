from datetime import date

import pandas as pd

from src.data.options import _fetch_bulk_eod, fetch_full_chain


class BulkClient:
    def __init__(self):
        self.eod_calls = []
        self.oi_calls = []

    def option_history_eod(self, **kwargs):
        self.eod_calls.append(kwargs)
        return pd.DataFrame(
            [
                {
                    "strike": 100.0,
                    "right": "CALL",
                    "bid": 4.9,
                    "ask": 5.1,
                    "close": 5.0,
                },
                {
                    "strike": 100.0,
                    "right": "PUT",
                    "bid": 4.4,
                    "ask": 4.6,
                    "close": 4.5,
                },
                {
                    "strike": 110.0,
                    "right": "CALL",
                    "bid": 0.0,
                    "ask": 0.0,
                    "close": 0.0,
                },
            ]
        )

    def option_history_open_interest(self, **kwargs):
        self.oi_calls.append(kwargs)
        return pd.DataFrame(
            [
                {"strike": 100.0, "right": "CALL", "open_interest": 20},
                {"strike": 100.0, "right": "PUT", "open_interest": 30},
            ]
        )


def test_fetch_bulk_eod_normalizes_and_filters_requested_rights():
    client = BulkClient()

    result = _fetch_bulk_eod(
        client,
        "TLT",
        date(2024, 2, 2),
        date(2024, 1, 2),
        ("P",),
    )

    assert result == {
        (100.0, "P"): {
            "bid": 4.4,
            "ask": 4.6,
            "close": 4.5,
            "option_price": 4.5,
            "price_type": "mid",
        }
    }
    assert client.eod_calls[0]["strike"] == "*"
    assert client.eod_calls[0]["right"] == "put"


def test_fetch_full_chain_uses_one_bulk_eod_call_per_expiry(tmp_path):
    client = BulkClient()
    snap = date(2024, 1, 2)
    expiry = date(2024, 2, 2)

    chain = fetch_full_chain(
        "TLT",
        snap,
        client,
        underlying=100.0,
        rf_annual=0.05,
        div_yield=0.0,
        rights=("C", "P"),
        cache_dir=tmp_path,
        expirations=[expiry],
    )

    assert len(client.eod_calls) == 1
    assert client.eod_calls[0]["strike"] == "*"
    assert client.eod_calls[0]["right"] == "both"
    assert len(client.oi_calls) == 1
    assert set(chain["right"]) == {"C", "P"}
    assert dict(zip(chain["right"], chain["open_interest"])) == {"C": 20, "P": 30}
