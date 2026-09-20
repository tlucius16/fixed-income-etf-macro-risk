"""Acquisition safety checks using fake vendor responses; no credentials/network."""
from argparse import Namespace
import json

import pandas as pd
import pytest

from scripts import pull_liquid_options as pull


def parameters():
    return dict(symbol="LQD", start_date="2025-01-02", end_date="2025-01-02",
                expiration="*", strike="*", right="both")


class Source:
    def __init__(self, failure=None):
        self.calls = []
        self.failure = failure

    def fetch(self, endpoint, params):
        self.calls.append((endpoint, params))
        if self.failure:
            raise self.failure
        frame = pd.DataFrame({"symbol": [params["symbol"]] * 2,
                              "expiration": ["2025-01-31"] * 2,
                              "strike": [100.0, 101.0], "right": ["CALL", "PUT"]})
        if endpoint == "eod":
            frame["created"] = params["start_date"] + "T17:15:00.000"
            frame["bid"] = [0.0, 1.0]
            frame["ask"] = [0.2, 1.1]
            frame["implied_vol"] = [None, None]
        else:
            frame["timestamp"] = params["start_date"] + "T06:30:00.000"
            frame["open_interest"] = [0.0, None]
        return frame


def args(root, **changes):
    values = dict(output=root, tickers=["LQD"], dates=["2025-01-02"], start=None,
                  end=None, max_dte=None, greeks=False, backend="sdk", base_url="unused",
                  dry_run=False, retry_empty=False)
    return Namespace(**(values | changes))


def test_preserves_zero_bid_missing_iv_and_missing_vs_zero_oi(tmp_path):
    source = Source()
    assert pull.run(args(tmp_path), source) == 0
    eod = pd.read_csv(tmp_path / "LQD/2025-01-02/eod.csv.gz")
    oi = pd.read_csv(tmp_path / "LQD/2025-01-02/open_interest.csv.gz")
    assert len(eod) == 2 and eod.bid.iloc[0] == 0 and eod.implied_vol.isna().all()
    assert oi.open_interest.iloc[0] == 0 and pd.isna(oi.open_interest.iloc[1])
    assert oi.timestamp.iloc[0] == "2025-01-02T06:30:00.000"
    assert len(source.calls) == 2
    for _, params in source.calls:
        assert params["strike"] == params["expiration"] == "*"
        assert params["right"] == "both" and "max_dte" not in params


def test_resume_verifies_partitions_and_does_not_fetch_again(tmp_path):
    source = Source()
    pull.run(args(tmp_path), source)
    pull.run(args(tmp_path), source)
    assert len(source.calls) == 2
    (tmp_path / "LQD/2025-01-02/eod.csv.gz").write_bytes(b"damaged")
    with pytest.raises(ValueError, match="Damaged"):
        pull.run(args(tmp_path), source)
    assert len(source.calls) == 2


def test_permission_failure_is_not_empty_data_and_is_retried_on_resume(tmp_path):
    source = Source(RuntimeError("PERMISSION_DENIED secret-password"))
    assert pull.run(args(tmp_path), source) == 2
    record = json.loads((tmp_path / "LQD/2025-01-02/eod.json").read_text())
    assert record["status"] == "permission_denied"
    assert "secret-password" not in json.dumps(record)
    assert len(source.calls) == 1
    source.failure = None
    assert pull.run(args(tmp_path), source) == 0
    assert len(source.calls) == 3


def test_no_data_is_recorded_separately_and_can_be_retried(tmp_path):
    source = Source(RuntimeError("NO_DATA"))
    record = pull.acquire(tmp_path, "eod", parameters(), source)
    assert record["status"] == "no_data"
    source.failure = None
    assert pull.acquire(tmp_path, "eod", parameters(), source)["status"] == "no_data"
    assert len(source.calls) == 1
    assert pull.acquire(tmp_path, "eod", parameters(), source, retry_empty=True)["rows"] == 2


def test_wrong_date_and_error_body_do_not_pass_as_valid_data():
    params = parameters()
    frame = Source().fetch("eod", params)
    frame["created"] = "2025-01-03T17:15:00"
    with pytest.raises(ValueError, match="different observation date"):
        pull.validate_frame(frame, "eod", params)
    with pytest.raises(ValueError, match="Missing response columns"):
        pull.validate_frame(pd.DataFrame(columns=["PERMISSION_DENIED"]), "eod", params)


def test_changed_plan_or_unrelated_directory_is_refused(tmp_path):
    pull.run(args(tmp_path), Source())
    with pytest.raises(ValueError, match="different plan"):
        pull.run(args(tmp_path, max_dte=90), Source())
    other = tmp_path / "unrelated"
    other.mkdir()
    (other / "old-cache.json").write_text("[]")
    with pytest.raises(ValueError, match="nonempty"):
        pull.run(args(other), Source())


def test_weekday_plan_keeps_holidays_and_dry_run_does_not_write(tmp_path):
    options = args(tmp_path / "new", dates=None, start="2025-01-01", end="2025-01-05",
                   dry_run=True)
    assert pull.make_plan(options)["dates"] == ["2025-01-01", "2025-01-02", "2025-01-03"]
    assert pull.run(options) == 0
    assert not options.output.exists()


def test_transient_failure_retries_without_losing_data(tmp_path, monkeypatch):
    source = Source()
    original = source.fetch
    attempts = []

    def flaky(endpoint, params):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("RESOURCE_EXHAUSTED")
        return original(endpoint, params)

    source.fetch = flaky
    monkeypatch.setattr(pull.time, "sleep", lambda seconds: None)
    record = pull.acquire(tmp_path, "eod", parameters(), source)
    assert record["status"] == "ok" and record["attempts"] == 2
    assert "error_type" not in record


def test_rest_routes_and_access_failures(tmp_path):
    class Session:
        denied = False

        def get(self, url, params, timeout):
            assert url.endswith("/option/history/greeks/eod")
            assert params["format"] == "csv" and params["right"] == "both"
            assert timeout == (10, 180)
            return Namespace(status_code=403 if self.denied else 200,
                             text="Forbidden" if self.denied else
                             Source().fetch("greeks_eod", parameters()).to_csv(index=False))

    source = pull.RESTSource("http://127.0.0.1:25503/v3")
    source.session = Session()
    assert pull.acquire(tmp_path, "greeks_eod", parameters(), source)["rows"] == 2
    source.session.denied = True
    assert pull.acquire(tmp_path / "denied", "greeks_eod", parameters(), source)["status"] == "permission_denied"
