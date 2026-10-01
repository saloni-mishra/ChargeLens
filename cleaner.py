import re

PREFIX_PATTERNS = [
    r'^(UPI|POS|ACH|NEFT|IMPS|INB|BIL)\s*[-/:]?\s*',
    r'\d{6,}X+\d{4}',
    r'/\d{10,}/',
]

def clean_merchant_string(raw: str) -> str:
    cleaned = raw.strip()
    
    # 1. Strip common transaction / channel prefixes
    for pattern in PREFIX_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
    # 2. FIX: Don't swallow hyphenated words before @
    # [\w.]+ only matches letters, numbers, underscores, and dots before @
    # Hyphens (-) now act as delimiters, preserving 'SPOTIFY' in 'SPOTIFY-RECURRING@paytm'
    cleaned = re.sub(r'[\w.]+@[\w.-]+', '', cleaned)
    
    # 3. Strip common noise words and geographic suffixes
    cleaned = re.sub(r'\b(MUMBAI|BANGALORE|BENGALURU|DELHI|IN|HYDERABAD|GURGAON|NOIDA|RECURRING|PAYMENT|MKTPLACE)\b', '', cleaned, flags=re.IGNORECASE)
    
    # 4. Collapse whitespace and strip dangling punctuation
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' -/*')
    return cleaned