import numpy as np
import pandas as pd
from typing import List, Dict, Any

def analyze_recurring_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = df['amount'].abs()
    df = df.sort_values(by=['normalized_merchant', 'date'])
    
    candidates = []
    for merchant, group in df.groupby('normalized_merchant'):
        if len(group) < 3:
            continue
            
        amounts = group['amount'].tolist()
        dates = group['date'].tolist()
        
        intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
        mean_interval = float(np.mean(intervals))
        std_interval = float(np.std(intervals))
        
        # Monthly regularity filter (allowing 26-35 days for varying calendar lengths)
        if 26 <= mean_interval <= 35:
            cadence = "monthly"
        else:
            continue
            
        mean_amount = float(np.mean(amounts))
        std_amount = float(np.std(amounts))
        cv_amount = (std_amount / mean_amount) if mean_amount > 0 else 1.0
        
        # Interval score drops if std_interval exceeds 3-5 days
        interval_score = max(0.0, 1.0 - (std_interval / 5.0))
        # Amount score drops if CV > 0
        amount_score = max(0.0, 1.0 - (cv_amount * 2.0))
        confidence = round((0.6 * interval_score + 0.4 * amount_score) * 100, 1)
        
        if confidence >= 70.0:
            candidates.append({
                "merchant": merchant,
                "user_amount": round(mean_amount, 2),
                "user_currency": group['currency'].iloc[0],
                "cadence": cadence,
                "occurrences": len(dates),
                "avg_interval": round(mean_interval, 1),
                "amount_variation_pct": round(cv_amount * 100, 1),
                "recurring_confidence": confidence,
                "dates": [d.strftime("%Y-%m-%d") for d in dates]
            })
            
    return candidates