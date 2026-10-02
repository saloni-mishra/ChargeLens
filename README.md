# ChargeLens

**Privacy-first recurring charge discovery & market evidence validation.**

ChargeLens analyzes bank statements locally to detect recurring charges, identify subscription services, track observed charge changes over time, and compare current public pricing using SerpApi.

Only a **canonical service name** such as `Netflix`, `Spotify`, or `YouTube Premium` is sent to the external search service. Raw transaction descriptions, dates, amounts, and account information stay local.

Gemini is used only as a **price-extraction/proposal layer**. A deterministic Python validator makes the final decision about what is shown to the user. When evidence is insufficient, ChargeLens reports `UNAVAILABLE` rather than guessing.

> Built for the **SerpApi India Hackathon 2026**  
> Track: **Commerce & Market Intelligence**

---

## 🚀 What ChargeLens Does

- Parse CSV bank statements
- Parse structured/text-based PDF statements
- Fall back to OCR for scanned/image-based PDFs
- Detect recurring monthly charges locally
- Measure recurrence confidence using interval regularity and amount stability
- Normalize merchant names locally
- Resolve known subscription/service identities locally
- Prevent unverified merchants from triggering external searches
- Detect observed historical charge transitions such as `₹199 → ₹249 → ₹299`
- Clearly distinguish observed statement changes from confirmed merchant price changes
- Search current public pricing through SerpApi
- Extract candidate pricing information using Gemini
- Ground proposed prices against the actual search-result text
- Validate pricing deterministically using Python
- Check currency and billing cadence
- Match charges against listed subscription plans
- Surface potentially cheaper listed tiers
- Flag eligibility-restricted tiers such as student or senior plans
- Show evidence and provenance for each comparison
- Estimate monthly and annual recurring spend
- Track SerpApi usage
- Enforce a SerpApi search budget
- Cache pricing evidence to avoid unnecessary searches
- Keep sensitive financial transaction data out of external search requests

---

## 🔐 Privacy-First Architecture

ChargeLens is designed around a strict privacy boundary.

### Data that stays local

The following information is processed locally and is not sent to SerpApi:

- Transaction dates
- Transaction amounts
- Currency
- Raw transaction descriptions
- Account/card references appearing in descriptions
- UPI IDs
- Transaction history
- Merchant normalization
- Recurring-charge detection
- Historical charge-change analysis
- Spending calculations

### Data that can leave the application

Only a canonical service identity is used for external pricing searches.

For example:

```text
Netflix
Spotify
YouTube Premium
```

The application does not send a raw transaction such as:

```text
UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm
```

or:

```text
2026-04-05, ₹649, UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm
```

Instead, after local merchant resolution, the external search is based on the canonical service name and public pricing intent.

This privacy boundary is also covered by an automated privacy test rather than being only a documentation claim.

## 🧠 AI Safety Boundary

ChargeLens deliberately separates AI extraction from the final decision.

```text
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
      ├── Historical charge-change detection
      │
      ▼
Canonical Service Identity
      │
      │
      ├──────── Private financial data stays local
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
      │  grounded against source text
      ▼
Deterministic Python Validator
      │
      ▼
User-visible Result + Evidence
```

### Gemini's role

Gemini proposes structured pricing information from the retrieved search evidence.

For example:

```text
Plan: Premium
Price: ₹299
Currency: INR
Cadence: monthly
Eligibility: student
```

However, Gemini does not decide whether the result is valid.

Before a proposed price reaches the validator, ChargeLens checks that the proposed price is grounded in the retrieved search-result text. A price that cannot be grounded in the source text is discarded.

### Deterministic validation

The Python validator checks:

- Required fields
- Price validity
- Currency
- Billing cadence
- Plan matching
- Eligibility restrictions
- Search/evidence availability
- Whether a listed plan actually matches the user's recurring charge

If the evidence cannot be safely validated, ChargeLens reports:

```text
UNAVAILABLE
```

rather than inventing or assuming a price.

The UI also distinguishes between:

- Search performed
- Price extracted

so that an unavailable result does not imply that a search was never attempted.

---

## 📄 Statement Input

ChargeLens supports three statement-processing paths.

### CSV

CSV files must provide these canonical fields:

```text
date
amount
currency
raw_description
```

Example:

```csv
date,amount,currency,raw_description
2026-04-05,299,INR,UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm
2026-05-05,299,INR,UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm
2026-06-05,299,INR,UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm
```

### Structured PDF

ChargeLens first attempts to extract transaction tables from text-based PDFs using pdfplumber.

### Image-based PDF / OCR

If a transaction table cannot be extracted, ChargeLens can fall back to OCR:

```text
PDF
 │
 ▼
PyMuPDF rendering
 │
 ▼
Tesseract OCR
 │
 ▼
OCR transaction parsing
 │
 ▼
Canonical transaction DataFrame
```

OCR accuracy depends on the scan quality, layout, fonts, and statement format.

---

## 🔎 Recurring Charge Detection

Recurring charges are detected locally before any external search is considered.

The detector uses:

- Billing interval regularity
- Amount stability
- Monthly cadence

A repeated merchant name alone is not sufficient.

For example:

```text
Netflix   ₹649   Apr
Netflix   ₹649   May
Netflix   ₹649   Jun
```

can be identified as a recurring monthly charge.

The recurring confidence score combines:

- 60% interval regularity
- 40% amount stability

The current charge used for spend calculations and market comparison is the most recently observed amount, rather than a historical average.

---

## 📈 Historical Charge Change Detection

ChargeLens separately tracks changes observed in recurring transaction amounts.

For example:

```text
₹199 → ₹199 → ₹249 → ₹249 → ₹299
```

produces observed transitions such as:

```text
₹199 → ₹249   +₹50 (+25.1%)
₹249 → ₹299   +₹50 (+20.1%)
```

These changes are based only on the transaction history in the statement.

### Important distinction

ChargeLens does not claim that an observed amount change was caused by an official merchant price increase.

The change could instead reflect:

- A plan upgrade
- Added services
- Taxes
- A billing adjustment
- Another transaction-level change

Therefore the dashboard explicitly describes these as observed charge changes, not confirmed merchant price changes.

The latest observed charge is used for:

- Monthly recurring spend
- Annualized recurring spend
- Current market-price comparison

The historical amounts remain visible separately as evidence.

---

## 🌐 SerpApi Integration

ChargeLens uses SerpApi to retrieve current public search results through Google Search.

Searches use India-focused parameters:

```text
gl=in
hl=en
```

The pricing search intent is based on the canonical service name.

For example:

```text
Netflix subscription plans India monthly price official
```

The original bank transaction description is never included in the search query.

### Search controls

ChargeLens uses:

- Disk caching
- Search budget limits
- Demonstration reserve
- Cache freshness controls
- Search throttling
- Audit logging

This prevents every recurring transaction from automatically consuming a paid search.

---

## 💰 SerpApi Budget Protection

The default configuration is:

```env
SERPAPI_TOTAL_BUDGET=250
SERPAPI_DEMO_RESERVE=50
```

Before making a live search, ChargeLens checks:

- Whether valid cached evidence already exists
- Whether the SerpApi budget permits another search

If the search cannot be performed because of budget restrictions, the application reports:

```text
SEARCH_THROTTLED
```

instead of silently retrying or pretending that pricing evidence was checked.

The dashboard also displays live usage, for example:

```text
SerpApi Used: 3 / 250
Reserve: 50
```

---

## ♻️ Replay Mode

ChargeLens supports replay mode for deterministic demos and development.

Replay mode reuses previously captured SerpApi responses instead of making a new live search.

The environment variable used by the current application is:

```env
ChargeLens_REPLAY=1
```

for replay mode, or:

```env
ChargeLens_REPLAY=0
```

for normal live-search operation.

Replay mode does not bypass the pricing extraction or deterministic validation pipeline.

---

## 🛡️ Validation States

ChargeLens does not force a comparison when evidence is insufficient.

Possible validation states include:

- `MATCHES_LISTED_PLAN`
- `NO_LISTED_MATCH`
- `NO_PRICE_FOUND`
- `GATE_MISMATCH`
- `IDENTITY_UNVERIFIED`
- `SEARCH_THROTTLED`

### MATCHES_LISTED_PLAN

The user's current charge matches a validated listed plan.

### NO_LISTED_MATCH

Pricing evidence was extracted, but the user's charge does not match a currently listed plan.

### NO_PRICE_FOUND

A search was performed, but no pricing information could be extracted and validated with sufficient confidence.

### GATE_MISMATCH

Evidence exists, but one or more required comparison conditions do not match, such as currency or billing cadence.

### IDENTITY_UNVERIFIED

The merchant could not be confidently resolved to a known service locally.

In this case:

- No external search is made.

This protects both user privacy and the SerpApi budget.

### SEARCH_THROTTLED

A search was required, but the budget guard prevented the external request.

---

## 🖥️ Dashboard

The dashboard presents the analysis pipeline and evidence in one view.

### Summary metrics

The dashboard shows:

- Recurring charges detected
- Monthly recurring spend
- Annualized recurring spend
- Unconfirmed price gap

The monthly and annual spend figures use the most recently observed recurring charge.

Potential differences from an unconfirmed plan are excluded from verified savings.

### "How ChargeLens Decides"

The dashboard visually presents the five-step decision pipeline:

1. Parse locally
2. Detect recurrence
3. Resolve service
4. Gather evidence
5. Validate

This makes the privacy and validation architecture visible rather than leaving it only in documentation.

### Merchant cards

Each recurring merchant card shows:

- Service name
- Current monthly charge
- Confidence tier
- Plain-English result summary

### Evidence drawer

Each merchant can expose detailed evidence including:

- Recurring detection information
- Billing cadence
- Amount stability
- Search status
- Price extraction status
- Historical charge transitions
- Market-price validation gates
- Matched plan
- Potential difference
- Cheaper listed tiers
- Eligibility caveats
- Search query
- Evidence source
- Retrieval timestamp
- Extraction model
- Validation method

---

## 📊 Example

Suppose a bank statement contains:

```text
UPI-NETFLIX.COM*9812-MUMBAI-paytm@paytm
```

ChargeLens processes the description locally and resolves it to:

```text
Netflix
```

The external pricing search is then based on:

```text
Netflix subscription plans India monthly price official
```

The raw transaction description and transaction amount are not included in the external search.

A result could appear as:

```text
Netflix — ₹299/month — UNAVAILABLE

Historical charge change:
₹199 → ₹249 → ₹299

Search performed: Yes
Price extracted: No

Public pricing was searched, but no subscription
price could be extracted and validated with
sufficient confidence.
```

If valid pricing evidence is available and the user's charge matches a listed plan, the dashboard can instead show a validated plan comparison and any potentially cheaper listed tiers, with eligibility caveats where applicable.

---

## 🏗️ Architecture

```text
                    ┌──────────────────────┐
                    │    Bank Statement    │
                    │    CSV / PDF / OCR   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Local Parser      │
                    │    CSV / PDF / OCR   │
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
                    │ + Charge Changes     │
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
                 IDENTITY_     Cache / Budget
                 UNVERIFIED          │
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
                              Dashboard + Evidence
```

---

## 🧩 Project Structure

```text
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
│   └── test_privacy.py
│
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🧰 Tech Stack

### Backend

- Python
- FastAPI
- Uvicorn
- Pandas
- NumPy

### Statement processing

- pdfplumber
- PyMuPDF
- pytesseract
- Pillow

### AI

- Google Gemini
- `gemini-2.5-flash`

Gemini is used for structured pricing extraction only. The final comparison decision is made by deterministic Python validation.

### Search

- SerpApi
- Google Search engine

### Frontend

- HTML
- CSS
- JavaScript

### Testing

- Pytest

---

## 🛠️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/saloni-mishra/ChargeLens
cd ChargeLens
```

### 2. Create a virtual environment

#### Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

---

## 🧾 OCR Setup

ChargeLens uses Tesseract for OCR fallback.

Install the Tesseract OCR engine separately for your operating system.

Verify the installation with:

```bash
tesseract --version
```

### Windows

A common installation path is:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If Tesseract is installed elsewhere, update the parser configuration accordingly.

### macOS

```bash
brew install tesseract
```

### Debian / Ubuntu

```bash
sudo apt install tesseract-ocr
```

OCR results can vary depending on statement layout and image quality.

---

## 🔑 Environment Variables

Create a local `.env` file.

Do not commit this file.

```env
SERPAPI_KEY=your_serpapi_key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
SERPAPI_TOTAL_BUDGET=250
SERPAPI_DEMO_RESERVE=50
ChargeLens_REPLAY=0
ChargeLens_DEMO=0
```

The variable names above match the names currently read by the application.

For the public repository, use:

```text
.env.example
```

with empty API-key values.

---

## ▶️ Run the Application

Start the FastAPI application with:

```bash
python -m uvicorn app:app --reload
```

Then open the local dashboard in your browser.

---

## 🧪 Run Tests

Run the complete test suite with:

```bash
python -m pytest -q
```

The test suite covers areas including:

- CSV parsing
- Structured PDF parsing
- OCR fallback
- Privacy boundary checks
- Recurring charge detection
- Historical charge transitions
- Latest-charge handling
- Pricing validation behavior

The privacy tests specifically verify that sensitive transaction information is not included in external search queries.

---

## 🔒 Security and Privacy Notes

The following information should never be included in external search requests:

- Account numbers
- Card numbers
- Transaction amounts
- Transaction dates
- Raw bank descriptions
- UPI IDs
- Personal identifiers
- Other private transaction metadata

Only the canonical service identity is used for external pricing searches.

Do not commit:

```text
.env
ChargeLens.db
personal bank statements
OCR output containing private information
private search/replay data
```

The repository `.gitignore` is configured to exclude local environment files, the SQLite database, Python cache files, and replay data.

---

## ⚠️ Limitations

ChargeLens is a hackathon prototype and has several known limitations.

### Merchant identification

Some merchants cannot be confidently mapped to a known service. These are reported as:

```text
IDENTITY_UNVERIFIED
```

rather than guessed.

### OCR

OCR accuracy depends on:

- PDF resolution
- Scan quality
- Fonts
- Table layout
- Statement format

The current OCR parser targets common transaction layouts and is not guaranteed to support every bank statement format.

### Public pricing

Public prices can change and search results can contain:

- Regional restrictions
- Promotional pricing
- Student plans
- Family plans
- Annual plans
- Other eligibility conditions

ChargeLens uses validation gates before presenting comparisons and explicitly flags eligibility-restricted tiers.

### Search availability

SerpApi searches are budget-controlled.

When the budget guard prevents a search, the result is:

```text
SEARCH_THROTTLED
```

### Detection scope

The current recurring detector focuses on monthly recurring charges that appear repeatedly within the available statement history.

Annual subscriptions that appear only once per year may not be identified.

### Historical charge changes

ChargeLens reports observed transitions in recurring transaction amounts.

It does not attempt to determine the cause of those changes.

For example:

```text
₹199 → ₹249
```

does not automatically mean:

```text
"the merchant increased its official price"
```

The application intentionally leaves the cause unresolved unless separate evidence establishes it.

---

## 🤖 AI Usage

ChargeLens uses Google Gemini (`gemini-2.5-flash`) to extract structured pricing information from SerpApi search evidence.

The extracted structure can contain:

- Plan
- Price
- Currency
- Billing period
- Eligibility

Gemini's output is grounded against the retrieved search text before being used.

The final user-facing comparison is determined by deterministic Python validation rather than by the model's judgment.

During development, Gemini and ChatGPT were also used for implementation assistance, debugging, documentation, and code review.

---

## 🏆 Hackathon Context

ChargeLens was built for the:

**SerpApi India Hackathon 2026**

Track: **Commerce & Market Intelligence**

The project demonstrates a privacy-conscious market-intelligence workflow:

```text
Private financial data
        │
        ▼
Local analysis
        │
        ▼
Canonical service identity
        │
        ▼
Public market evidence
        │
        ▼
AI-assisted extraction
        │
        ▼
Deterministic validation
        │
        ▼
Evidence-backed result
```

The core principle is:

> Keep private financial data local. Use the public web only for public pricing evidence.

---

## 📜 License

This project is released under the MIT License.

See `LICENSE` for the full license text.

---

## 👤 Author

Built for the SerpApi India Hackathon 2026.
