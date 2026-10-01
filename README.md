# StatementIQ

### Privacy-first bank statement analyzer for recurring charges and price checks

StatementIQ is a privacy-first bank statement analyzer built for the **SerpApi India Hackathon 2026**.

It helps users understand recurring expenses in their bank statements and compare subscription prices with currently listed public prices in India.

The key design goal is simple:

> **Keep private financial data local. Use the web only for public pricing information.**

StatementIQ processes bank statement data locally, detects recurring merchants, resolves canonical merchant identities, and only sends the canonical service name to SerpApi when an external price lookup is needed.

Gemini can propose structured price information from search results, but a deterministic Python validator makes the final decision about what is shown to the user.

---

## 🚀 What StatementIQ Does

StatementIQ can:

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

---

## 🔐 Privacy-First Architecture

StatementIQ is designed around a strict privacy boundary.

### What stays local

The following information is processed locally:

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

Only a **canonical merchant/service name** is sent to SerpApi.

For example:

```text
Netflix
Spotify
YouTube Premium

StatementIQ does not send:

UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm

or:

2026-04-05, ₹649, UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm

to the external search service.

The external search query is based on the canonical service identity and public pricing intent.

🧠 AI Safety Boundary

StatementIQ uses Gemini as a proposal/extraction layer, not as the final decision-maker.

The flow is:
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

Gemini may propose:

Plan: Premium
Price: ₹299/month
Currency: INR
Cadence: monthly
Eligibility: student

But Gemini cannot directly decide that the result is valid.

The Python validator checks:

Price validity
Currency
Billing cadence
Plan matching
Eligibility restrictions
Required fields
Search/evidence availability

If the data cannot be safely validated, StatementIQ shows:
UNAVAILABLE
rather than guessing.
📄 Statement Input

StatementIQ supports three input paths.

CSV

CSV files must provide the following canonical fields:

date
amount
currency
raw_description
Structured PDF

StatementIQ first attempts to extract transaction tables from PDFs using pdfplumber.

Image-based PDF / OCR

If no transaction table can be extracted, StatementIQ falls back to:

PDF
 ↓
PyMuPDF rendering
 ↓
Tesseract OCR
 ↓
OCR transaction parsing
 ↓
Canonical transaction DataFrame

OCR accuracy can vary depending on the layout and quality of the bank statement.

For Windows, the Tesseract OCR engine must be installed separately. The Python package pytesseract provides the Python interface to Tesseract.

🔎 Recurring Charge Detection

Recurring transactions are detected locally.

StatementIQ looks for repeated merchant activity and recurring payment patterns before considering any external search.

Example:

Netflix       ₹649   Apr
Netflix       ₹649   May
Netflix       ₹649   Jun

can be identified as a recurring charge.

The application can then investigate whether the merchant corresponds to a known subscription/service.

🌐 SerpApi Integration

StatementIQ uses SerpApi to retrieve current public search results.

The current search flow uses Google Search through SerpApi with India-focused parameters.

Example search intent:

"<service> subscription plans India monthly price official"

The application does not send raw transaction descriptions to SerpApi.

Search controls

StatementIQ uses:

Disk caching
Search budget limits
Budget reserve for demonstrations
Cache freshness controls
Search throttling
Audit information

This prevents every transaction from automatically triggering a paid external search.

💰 SerpApi Budget Protection

The application uses a configurable search budget.

Example:

SERPAPI_TOTAL_BUDGET=250
SERPAPI_DEMO_RESERVE=50

The application checks cache and budget availability before making a SerpApi request.

If a search cannot be performed because of the budget, the UI reports:

SEARCH_THROTTLED

rather than silently making an additional API request.

♻️ Replay Mode

For deterministic demos and development, StatementIQ supports replay mode.

STATEMENTIQ_REPLAY=0

Normal operation:

STATEMENTIQ_REPLAY=0

Replay/demo operation can use:

STATEMENTIQ_REPLAY=1

Replay mode allows previously captured search responses to be reused instead of repeatedly calling the external search API.

🛡️ Validation States

StatementIQ does not force a price comparison when evidence is insufficient.

Examples of validation states include:

MATCHES_LISTED_PLAN
NO_LISTED_MATCH
NO_PRICE_FOUND
GATE_MISMATCH
IDENTITY_UNVERIFIED
SEARCH_THROTTLED

For example, if a merchant cannot be confidently identified locally:

IDENTITY_UNVERIFIED

No external search is made.

This protects both privacy and the SerpApi budget.

📊 Example

A recurring statement entry might contain:

UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm

StatementIQ can locally resolve this to:

Netflix

The application can then search public pricing information for:

Netflix subscription plans India monthly price official

The user's original transaction description is not sent to SerpApi.

The resulting dashboard can show information such as:

Netflix
₹649/month

Confidence: MEDIUM

Nearest listed plan:
Basic — ₹199/month

Potential price difference:
₹450/month

If a valid price cannot be established, StatementIQ instead displays:

UNAVAILABLE
🏗️ Architecture
                    ┌──────────────────────┐
                    │   Bank Statement     │
                    │   CSV / PDF / OCR     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Local Parser       │
                    │ CSV / PDF / OCR      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Merchant Normalizer  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Recurring Detector   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Canonical Service    │
                    │ Identity             │
                    └──────────┬───────────┘
                               │
                     Searchable?
                       /       \
                     No         Yes
                     │           │
                     ▼           ▼
               UNVERIFIED   Cache / Budget
                                 │
                                 ▼
                             SerpApi
                                 │
                                 ▼
                         Search Results
                                 │
                                 ▼
                             Gemini
                        Price Proposal Only
                                 │
                                 ▼
                    Deterministic Validator
                                 │
                                 ▼
                         Dashboard Result
🧩 Project Structure
StatementIQ/
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
│   └── test_ocr_fallback.py
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
⚙️ Tech Stack
Backend
Python
FastAPI
Uvicorn
Pandas
NumPy
Statement Processing
pdfplumber
PyMuPDF
pytesseract
Pillow
AI
Google Gemini
Search
SerpApi
Google Search
Frontend
HTML
CSS
JavaScript
Testing
Pytest
🛠️ Setup
1. Clone the repository
git clone <your-public-github-repository>
cd StatementIQ
2. Create a virtual environment

Windows:

py -3.12 -m venv .venv

Activate it:

.venv\Scripts\Activate.ps1
3. Install Python dependencies
python -m pip install -r requirements.txt
🧾 OCR Setup on Windows

StatementIQ uses Tesseract for OCR fallback.

Install the Tesseract OCR engine separately.

After installation, verify:

tesseract --version

StatementIQ currently uses the standard Windows installation path:

C:\Program Files\Tesseract-OCR\tesseract.exe

If your installation uses another location, update the Tesseract path in the parser configuration.

🔑 Environment Variables

Create a local .env file:

SERPAPI_KEY=your_serpapi_key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

SERPAPI_TOTAL_BUDGET=250
SERPAPI_DEMO_RESERVE=50

STATEMENTIQ_REPLAY=0
STATEMENTIQ_DEMO=0

Never commit your real .env file.

Use .env.example for the public repository.

Example:

SERPAPI_KEY=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

SERPAPI_TOTAL_BUDGET=250
SERPAPI_DEMO_RESERVE=50

STATEMENTIQ_REPLAY=0
STATEMENTIQ_DEMO=0
▶️ Run the Application

Start the FastAPI application:

python -m uvicorn app:app --reload

Then open the local dashboard in your browser.

🧪 Run Tests

Run the complete test suite:

python -m pytest -q

Current parser coverage includes:

CSV parsing
PDF table parsing
PDF OCR fallback

The project currently has:

4 passed
🔒 Security and Privacy Notes

StatementIQ is designed to minimize external exposure of financial information.

The following should never be included in external search requests:

Account numbers
Card numbers
Transaction amounts
Transaction dates
Raw bank descriptions
UPI IDs
Personal identifiers

Only the canonical service identity should be used for external pricing searches.

Users should also avoid committing:

.env
statementiq.db
personal bank statements
OCR output containing private information
SerpApi replay data containing sensitive information
⚠️ Limitations

StatementIQ is a hackathon prototype and has several limitations.

Merchant identification

Some merchants may not be confidently identifiable from a transaction description.

These are marked:

IDENTITY_UNVERIFIED

rather than guessed.

OCR

OCR quality depends on:

PDF resolution
scan quality
fonts
table layout
column arrangement
OCR recognition accuracy

The current OCR parser is designed around common transaction layouts and is not guaranteed to support every bank statement format.

Public pricing

Public subscription prices can change.

Search results may also contain:

regional restrictions
promotional pricing
student plans
family plans
annual plans
eligibility requirements

StatementIQ therefore uses validation gates before presenting a comparison.

Search availability

SerpApi searches are budget-controlled.

If the search budget is unavailable, the result can be:

SEARCH_THROTTLED
🤖 AI Usage

StatementIQ uses Gemini for structured information extraction from public search results.

Gemini is intentionally restricted to a proposal role.

The final displayed result is determined by deterministic Python validation logic.

AI assistance was also used during development for implementation, debugging, documentation, and code review.

🏆 Hackathon Context

Built for the SerpApi India Hackathon 2026.

The project demonstrates a privacy-conscious workflow where:

Private financial data
        ↓
Local processing
        ↓
Canonical service identity
        ↓
Public web search
        ↓
Structured extraction
        ↓
Deterministic validation
        ↓
Actionable dashboard

The goal is to combine local financial-data processing with current public web information without unnecessarily exposing sensitive transaction data.

📜 License

This project is released under the MIT License.

See LICENSE for the full license text.

👤 Author

Built for the SerpApi India Hackathon 2026.

