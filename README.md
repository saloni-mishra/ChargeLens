# ChargeLens

**Privacy-first bank statement analyzer for recurring charges and price checks.**

ChargeLens parses bank statements (CSV, structured PDF, or OCR fallback for scanned PDFs) entirely on-device, detects recurring charges, identifies the underlying subscription service, and checks current public pricing through SerpApi — sending only a canonical service name, never raw statement data. Gemini proposes structured price candidates from search results, but a deterministic Python validator makes the final decision about what the user sees, and shows `UNAVAILABLE` rather than guessing when evidence is insufficient.

> Built for the **SerpApi India Hackathon 2026**. Track: **Commerce & Market Intelligence**.

The key design goal is simple:

> Keep private financial data local. Use the web only for public pricing information.

## 🚀 What ChargeLens Does

- Parse CSV bank statements
- Parse structured/text-based PDF statements
- Fall back to OCR for image-based PDFs
- Detect recurring charges locally
- Normalize merchant names locally
- Identify potentially searchable subscription/services
- Search current public pricing using SerpApi
- Extract candidate prices using Gemini
- Validate extracted prices deterministically
- Compare the user's recurring payment with listed plans
- Show evidence and confidence
- Track SerpApi usage and enforce a search budget
- Cache search results to avoid unnecessary API calls
- Keep sensitive transaction information out of external search requests

## 🔐 Privacy-First Architecture

ChargeLens is designed around a strict privacy boundary.

### What stays local

- Transaction dates
- Transaction amounts
- Currency
- Raw transaction descriptions
- Account/card references appearing in descriptions
- Transaction history
- Merchant normalization
- Recurring-charge detection
- Spending calculations

### What can leave the application

Only a canonical merchant/service name is sent to SerpApi. For example: `Netflix`, `Spotify`, `YouTube Premium`.

ChargeLens does **not** send `UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm`, or `2026-04-05, ₹649, UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm`, to the external search service. The external search query is based solely on the canonical service identity and public pricing intent.

## 🧠 AI Safety Boundary

ChargeLens uses Gemini as a proposal/extraction layer, not as the final decision-maker.

```
Bank Statement
      │
      ▼
Local Parsing
      │
      ▼
Merchant Normalization
      │
      ▼
Recurring Charge Detection
      │
      ▼
Canonical Service Name
      │
      ├─────────────── Local/private data stays here
      │
      ▼
SerpApi Public Search
      │
      ▼
Search Results
      │
      ▼
Gemini Price Proposal
      │
      ▼
Deterministic Python Validator
      │
      ▼
User-visible Result
```

Gemini may propose something like:

```
Plan: Premium
Price: ₹299/month
Currency: INR
Cadence: monthly
Eligibility: student
```

But Gemini cannot directly decide that the result is valid. Before a proposal ever reaches the validator, each proposed price is **grounded against the raw search snippets** — any price the model proposes that doesn't literally appear in the source text is discarded, so the LLM can propose but can never fabricate.

The Python validator then checks:

- Price validity
- Currency
- Billing cadence
- Plan matching
- Eligibility restrictions
- Required fields
- Search/evidence availability

If the data cannot be safely validated, ChargeLens shows `UNAVAILABLE` rather than guessing.

## 📄 Statement Input

ChargeLens supports three input paths.

**CSV** — files must provide these canonical fields: `date`, `amount`, `currency`, `raw_description`.

**Structured PDF** — ChargeLens first attempts to extract transaction tables from PDFs using `pdfplumber`.

**Image-based PDF / OCR** — if no transaction table can be extracted, ChargeLens falls back to:

```
PDF → PyMuPDF rendering → Tesseract OCR → OCR transaction parsing → Canonical transaction DataFrame
```

OCR accuracy can vary depending on the layout and quality of the bank statement.

## 🔎 Recurring Charge Detection

Recurring transactions are detected locally, before any external search is considered. For example:

```
Netflix   ₹649   Apr
Netflix   ₹649   May
Netflix   ₹649   Jun
```

is identified as a recurring charge based on interval regularity and amount stability, not just a repeated name.

## 🌐 SerpApi Integration

ChargeLens uses SerpApi to retrieve current public search results via Google Search, with India-focused parameters (`gl=in`, `hl=en`). Example search intent:

```
"<service> subscription plans India monthly price official"
```

The application does not send raw transaction descriptions to SerpApi.

**Search controls:**
- Disk caching
- Search budget limits
- Budget reserve for demonstrations
- Cache freshness controls
- Search throttling
- Audit information

This prevents every transaction from automatically triggering a paid external search.

## 💰 SerpApi Budget Protection

```
SERPAPI_TOTAL_BUDGET=250
SERPAPI_DEMO_RESERVE=50
```

The application checks cache and budget availability before making a SerpApi request. If a search cannot be performed because of the budget, the UI reports `SEARCH_THROTTLED` rather than silently skipping or retrying.

## ♻️ Replay Mode

For deterministic demos and development, ChargeLens supports replay mode:

```
ChargeLens_REPLAY=1   # reuse previously captured search responses
ChargeLens_REPLAY=0   # normal operation — live SerpApi calls
```

## 🛡️ Validation States

ChargeLens does not force a price comparison when evidence is insufficient. Validation states include:

- `MATCHES_LISTED_PLAN`
- `NO_LISTED_MATCH`
- `NO_PRICE_FOUND`
- `GATE_MISMATCH`
- `IDENTITY_UNVERIFIED`
- `SEARCH_THROTTLED`

For example, if a merchant cannot be confidently identified locally, ChargeLens returns `IDENTITY_UNVERIFIED` and **no external search is made** — protecting both privacy and the SerpApi budget.

## 📊 Example

A recurring statement entry containing `UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm` is locally resolved to `Netflix`. ChargeLens then searches public pricing for `"Netflix subscription plans India monthly price official"` — the original transaction description is never sent to SerpApi.

The dashboard shows results like:

```
Netflix — ₹649/month — Confidence: MEDIUM
Nearest listed plan: Basic — ₹199/month
Your charge does not match any current listed price
```

If a valid price cannot be established, ChargeLens instead displays `UNAVAILABLE` with the specific reason (e.g. identity unverified, no price found, or search throttled).

## 🏗️ Architecture

```
                    ┌──────────────────────┐
                    │   Bank Statement      │
                    │   CSV / PDF / OCR     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Local Parser        │
                    │ CSV / PDF / OCR       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Merchant Normalizer   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Recurring Detector    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Canonical Service     │
                    │ Identity              │
                    └──────────┬───────────┘
                               │
                       Searchable?
                        /        \
                      No          Yes
                      │            │
                      ▼            ▼
               IDENTITY_      Cache / Budget
               UNVERIFIED          │
                                   ▼
                               SerpApi
                                   │
                                   ▼
                           Search Results
                                   │
                                   ▼
                               Gemini
                        (Price Proposal Only —
                         grounded against source text)
                                   │
                                   ▼
                      Deterministic Validator
                                   │
                                   ▼
                           Dashboard Result
```

## 🧩 Project Structure

```
ChargeLens/
│
├── app.py
├── statement_parser.py
├── cleaner.py
├── normalizer.py
├── detector.py
├── database.py
├── budget.py
├── search.py
├── extractor.py
├── validator.py
├── slice_runner.py
│
├── static/
│   └── index.html
│
├── tests/
│   ├── fixtures/
│   │   ├── sample.pdf
│   │   ├── sample_ocr.pdf
│   │   └── generate_ocr_pdf.py
│   │
│   ├── test_parser_csv.py
│   ├── test_parser_pdf.py
│   ├── test_ocr_fallback.py
│   └── test_privacy.py      # asserts SerpApi queries contain no amounts, dates, or raw statement text
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## ⚙️ Tech Stack

**Backend:** Python, FastAPI, Uvicorn, Pandas, NumPy
**Statement Processing:** pdfplumber, PyMuPDF, pytesseract, Pillow
**AI:** Google Gemini (`gemini-2.5-flash`) — structured extraction only, output grounded against source text, final decision made deterministically
**Search:** SerpApi (Google Search engine)
**Frontend:** HTML, CSS, JavaScript
**Testing:** Pytest

## 🛠️ Setup

### 1. Clone the repository

```bash
git clone <your-public-github-repository>
cd ChargeLens
```

### 2. Create a virtual environment

**Windows:**
```bash
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 🧾 OCR Setup

ChargeLens uses Tesseract for OCR fallback. Install the Tesseract OCR engine separately for your platform, then verify with:

```bash
tesseract --version
```

**Windows** default path: `C:\Program Files\Tesseract-OCR\tesseract.exe` — update the path in the parser configuration if your installation differs.
**macOS:** `brew install tesseract`
**Linux (Debian/Ubuntu):** `sudo apt install tesseract-ocr`

## 🔑 Environment Variables

Create a local `.env` file (never commit this):

```
SERPAPI_KEY=your_serpapi_key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

SERPAPI_TOTAL_BUDGET=250
SERPAPI_DEMO_RESERVE=50

ChargeLens_REPLAY=0
ChargeLens_DEMO=0
```

Use `.env.example` (with empty values) for the public repository.

## ▶️ Run the Application

```bash
python -m uvicorn app:app --reload
```

Then open the local dashboard in your browser.

## 🧪 Run Tests

```bash
python -m pytest -q
```

Current test coverage includes CSV parsing, PDF table parsing, PDF OCR fallback, and an automated privacy check confirming no financial data reaches the external search query.

## 🔒 Security and Privacy Notes

The following should never be included in external search requests: account numbers, card numbers, transaction amounts, transaction dates, raw bank descriptions, UPI IDs, personal identifiers. Only the canonical service identity is used for external pricing searches.

Users should also avoid committing: `.env`, `ChargeLens.db`, personal bank statements, OCR output containing private information, or SerpApi replay data containing sensitive information.

## ⚠️ Limitations

ChargeLens is a hackathon prototype with several known limitations:

**Merchant identification** — some merchants may not be confidently identifiable from a transaction description. These are marked `IDENTITY_UNVERIFIED` rather than guessed.

**OCR** — accuracy depends on PDF resolution, scan quality, fonts, and table layout. The current OCR parser targets common transaction layouts and is not guaranteed to support every bank statement format.

**Public pricing** — prices can change, and search results may reflect regional restrictions, promotional pricing, student/family plans, or annual plans. ChargeLens uses validation gates before presenting any comparison rather than assuming pricing is current or applicable.

**Search availability** — SerpApi searches are budget-controlled. If the budget is unavailable, the result is `SEARCH_THROTTLED`.

**Detection scope** — only monthly-cadence recurring charges are reliably detected from a single statement period; annual subscriptions appearing once per year may not be identified.

## 🤖 AI Usage

ChargeLens uses **Google Gemini (`gemini-2.5-flash`)** for structured information extraction from public search results. Gemini is intentionally restricted to a proposal role: its output is grounded against the raw search text before use, and the final displayed result is determined entirely by deterministic Python validation logic, not the model.

During development, **Gemini** and **Chatgpt** were used for implementation assistance, debugging, documentation, and code review.

## 🏆 Hackathon Context

Built for the **SerpApi India Hackathon 2026**, Commerce & Market Intelligence track. The project demonstrates a privacy-conscious workflow where private financial data stays local, only a canonical service identity reaches the public web, and every user-facing claim passes through deterministic validation before display — never an AI guess alone.

## 📜 License

This project is released under the MIT License. See `LICENSE` for the full license text.

## 👤 Author

Built for the SerpApi India Hackathon 2026.