import re

PREFIX_PATTERNS = [
    r'^(UPI|POS|ACH|NEFT|IMPS|INB|BIL)\s*[-/:]?\s*',
    r'\d{6,}X+\d{4}',
    r'/\d{10,}/',
]

def clean_merchant_string(raw: str) -> str:
    cleaned = raw.strip()
    for pattern in PREFIX_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\w\.-]+@[\w\.-]+', '', cleaned)
    cleaned = re.sub(r'\b(MUMBAI|BANGALORE|BENGALURU|DELHI|IN|HYDERABAD|GURGAON|NOIDA)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' -/*')
    return cleaned