import pandas as pd

from detector import analyze_recurring_patterns


def make_df(amounts):
    dates = pd.date_range(
        "2026-01-01",
        periods=len(amounts),
        freq="MS"
    )

    return pd.DataFrame({
        "date": dates,
        "amount": amounts,
        "currency": ["INR"] * len(amounts),
        "raw_description": ["Netflix"] * len(amounts),
        "normalized_merchant": ["Netflix"] * len(amounts),
    })


def test_detects_price_transitions():
    result = analyze_recurring_patterns(
        make_df([199, 499, 199, 699, 499])
    )

    assert len(result) == 1

    item = result[0]

    assert item["price_change_detected"] is True

    changes = item["price_changes"]

    assert len(changes) == 4

    assert changes[0]["previous_amount"] == 199
    assert changes[0]["current_amount"] == 499
    assert changes[0]["change_amount"] == 300
    assert changes[0]["change_pct"] == 150.8

    assert changes[1]["previous_amount"] == 499
    assert changes[1]["current_amount"] == 199

    assert changes[2]["previous_amount"] == 199
    assert changes[2]["current_amount"] == 699

    assert changes[3]["previous_amount"] == 699
    assert changes[3]["current_amount"] == 499


def test_detects_single_price_transition():
    result = analyze_recurring_patterns(
        make_df([499, 499, 649])
    )

    assert len(result) == 1

    item = result[0]

    assert item["price_change_detected"] is True
    assert len(item["price_changes"]) == 1
    assert item["price_changes"][0]["previous_amount"] == 499
    assert item["price_changes"][0]["current_amount"] == 649


def test_does_not_flag_stable_price():
    result = analyze_recurring_patterns(
        make_df([499, 499, 499, 499])
    )

    assert len(result) == 1

    item = result[0]

    assert item["price_change_detected"] is False
    assert item["price_changes"] == []


def test_amount_history_is_preserved():
    result = analyze_recurring_patterns(
        make_df([199, 499, 199, 699, 499])
    )

    history = result[0]["amount_history"]

    assert [x["amount"] for x in history] == [
        199, 499, 199, 699, 499
    ]

    assert history[0]["date"] == "2026-01-01"
    assert history[-1]["date"] == "2026-05-01"
def test_latest_charge_is_used_not_historical_average():
    result = analyze_recurring_patterns(
        make_df([199, 199, 249, 249, 299])
    )

    assert len(result) == 1
    assert result[0]["user_amount"] == 299
def test_confidence_uses_latest_price_segment():
    result = analyze_recurring_patterns(
        make_df([199, 199, 249, 249, 299, 299])
    )

    assert len(result) == 1

    # Latest segment is [299, 299], so current-price CV is zero.
    assert result[0]["amount_variation_pct"] == 0.0