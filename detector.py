import numpy as np
import pandas as pd
from typing import List, Dict, Any


def _detect_price_change(amounts, dates):
    rounded_amounts = [round(float(a), 2) for a in amounts]

    if len(rounded_amounts) < 2:
        return {
            "price_change_detected": False,
            "price_changes": [],
            "amount_history": [],
        }

    changes = []

    for i in range(1, len(rounded_amounts)):
        previous = rounded_amounts[i - 1]
        current = rounded_amounts[i]

        if previous == current:
            continue

        change_amount = round(current - previous, 2)

        if previous != 0:
            change_pct = round((change_amount / previous) * 100, 1)
        else:
            change_pct = None

        changes.append({
            "previous_amount": previous,
            "current_amount": current,
            "change_amount": change_amount,
            "change_pct": change_pct,
            "change_date": dates[i].strftime("%Y-%m-%d"),
        })

    return {
        "price_change_detected": bool(changes),
        "price_changes": changes,
        "amount_history": [
            {
                "date": d.strftime("%Y-%m-%d"),
                "amount": round(float(a), 2),
            }
            for d, a in zip(dates, amounts)
        ],
    }


def _latest_amount_segment(amounts):
    """
    Return the start/end indexes of the latest contiguous amount segment.

    Example:
        [199, 199, 249, 249, 299]
                         ^ latest segment = [299]

        [139, 139, 139, 159, 159]
                         ^^^^^^^^^ latest segment = [159, 159]
    """
    rounded = [round(float(a), 2) for a in amounts]

    if not rounded:
        return 0, -1

    latest = rounded[-1]
    start = len(rounded) - 1

    while start > 0 and rounded[start - 1] == latest:
        start -= 1

    return start, len(rounded) - 1


def analyze_recurring_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    df = df.copy()

    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].abs()

    df = df.sort_values(by=["normalized_merchant", "date"])

    candidates = []

    for merchant, group in df.groupby("normalized_merchant"):
        if len(group) < 3:
            continue

        amounts = group["amount"].tolist()
        dates = group["date"].tolist()

        intervals = [
            (dates[i] - dates[i - 1]).days
            for i in range(1, len(dates))
        ]

        mean_interval = float(np.mean(intervals))
        std_interval = float(np.std(intervals))

        if 26 <= mean_interval <= 35:
            cadence = "monthly"
        else:
            continue

        # ------------------------------------------------------------
        # Current charge
        # ------------------------------------------------------------
        # The headline amount must represent the latest known charge,
        # not the historical average across previous prices.
        latest_amount_start, latest_amount_end = _latest_amount_segment(amounts)

        latest_segment_amounts = amounts[
            latest_amount_start:latest_amount_end + 1
        ]

        current_amount = round(
            float(np.mean(latest_segment_amounts)),
            2
        )

        # ------------------------------------------------------------
        # Confidence
        # ------------------------------------------------------------
        # Timing regularity is evaluated over the complete history.
        interval_score = max(
            0.0,
            1.0 - (std_interval / 5.0)
        )

        # Amount stability is evaluated ONLY inside the latest
        # price segment. A historical price transition is therefore
        # not double-counted as ongoing instability.
        latest_mean_amount = float(np.mean(latest_segment_amounts))

        if latest_mean_amount > 0:
            latest_std_amount = float(np.std(latest_segment_amounts))
            cv_amount = latest_std_amount / latest_mean_amount
        else:
            cv_amount = 1.0

        amount_score = max(
            0.0,
            1.0 - (cv_amount * 2.0)
        )

        confidence = round(
            (0.6 * interval_score + 0.4 * amount_score) * 100,
            1
        )

        if confidence >= 70.0:
            price_change = _detect_price_change(amounts, dates)

            candidates.append({
                "merchant": merchant,

                # IMPORTANT:
                # This is now the latest known recurring charge,
                # not the historical average.
                "user_amount": current_amount,

                "user_currency": group["currency"].iloc[0],
                "cadence": cadence,
                "occurrences": len(dates),
                "avg_interval": round(mean_interval, 1),

                # This CV describes stability of the CURRENT price
                # segment, not historical price changes.
                "amount_variation_pct": round(cv_amount * 100, 1),

                "recurring_confidence": confidence,

                "dates": [
                    d.strftime("%Y-%m-%d")
                    for d in dates
                ],

                **price_change,
            })

    return candidates