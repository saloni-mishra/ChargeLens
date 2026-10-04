from __future__ import annotations

import os
import re
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd


REQUIRED_COLUMNS = {
    "date",
    "amount",
    "currency",
    "raw_description",
}


def parse_csv(source: str | Path | BinaryIO) -> pd.DataFrame:
    """
    Parse a ChargeLens CSV statement into the canonical transaction format.

    Expected columns:
        date, amount, currency, raw_description
    """
    df = pd.read_csv(source)

    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            f"CSV is missing required columns: {sorted(missing)}"
        )

    return _normalize_dataframe(df)


def parse_pdf(source) -> pd.DataFrame:
    """
    Parse a PDF statement.

    First attempts structured PDF table extraction.
    Falls back to OCR when no usable transaction rows are found.

    The PDF content is read once into bytes so the OCR fallback
    always receives the complete document.
    """
    import pdfplumber

    # Normalize every input type into immutable PDF bytes.
    if isinstance(source, (str, Path)):
        with open(source, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()

    elif isinstance(source, bytes):
        pdf_bytes = source

    elif isinstance(source, bytearray):
        pdf_bytes = bytes(source)

    else:
        # File-like object.
        current_position = source.tell() if hasattr(source, "tell") else None

        if hasattr(source, "seek"):
            source.seek(0)

        pdf_bytes = source.read()

        # Restore the original position when possible.
        if current_position is not None and hasattr(source, "seek"):
            source.seek(current_position)

    rows = []

    # Use a fresh BytesIO object for structured PDF extraction.
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                if not table:
                    continue

                rows.extend(_table_to_rows(table))

    if rows:
        df = pd.DataFrame(rows)
        return _normalize_dataframe(df)

    # IMPORTANT:
    # Pass the original complete PDF bytes to OCR.
    return _parse_pdf_with_ocr(pdf_bytes)

def _parse_pdf_with_ocr(source) -> pd.DataFrame:
    """
    Render PDF pages to images and extract transaction rows using Tesseract OCR.
    """
    import pymupdf
    import pytesseract
    from PIL import Image

    # Allow the Tesseract path to be overridden through the environment.
    # On Windows, fall back to the standard installation location.
    tesseract_cmd = os.getenv(
        "TESSERACT_CMD",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    )

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    if not os.path.exists(tesseract_cmd):
        raise RuntimeError(
            "Tesseract OCR was not found. "
            f"Expected executable at: {tesseract_cmd}. "
            "Set the TESSERACT_CMD environment variable to the correct path."
        )

    if isinstance(source, (str, Path)):
        pdf_source = str(source)

    elif isinstance(source, bytes):
        pdf_source = source

    else:
        pdf_source = source.read()

    if isinstance(pdf_source, (bytes, bytearray)):
        document = pymupdf.open(
            stream=pdf_source,
            filetype="pdf",
        )
    else:
        document = pymupdf.open(pdf_source)

    rows = []

    try:
        for page in document:
            # Render at 2x resolution for reliable OCR.
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2),
                alpha=False,
            )

            image = Image.frombytes(
                "RGB",
                [pixmap.width, pixmap.height],
                pixmap.samples,
            )

            text = pytesseract.image_to_string(
                image,
                config="--psm 6",
            )

            rows.extend(_ocr_text_to_rows(text))

    finally:
        document.close()

    if not rows:
        raise ValueError(
            "No transaction table or OCR transaction rows could be "
            "extracted from the PDF."
        )

    df = pd.DataFrame(rows)

    return _normalize_dataframe(df)


def _ocr_text_to_rows(text: str) -> list[dict]:
    """
    Convert OCR text into canonical transaction rows.

    Supports common layouts such as:

        2026-01-05 NETFLIX 649.00

    and:

        2026-01-05 NETFLIX 649.00 INR

    It also handles bank-statement lines containing additional
    reference/UPI information between the description and amount.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    rows = []

    for line in lines:
        # ---------------------------------------------------------
        # 1. Ignore obvious headers.
        # ---------------------------------------------------------
        lower_line = line.lower()

        if (
            "date narration" in lower_line
            or "date description" in lower_line
            or "transaction desc" in lower_line
            or "ref / chq" in lower_line
            or "debit (inr)" in lower_line
            or "credit (inr)" in lower_line
        ):
            continue

        if lower_line in {
            "date",
            "description",
            "amount",
            "currency",
            "narration",
        }:
            continue

        # ---------------------------------------------------------
        # 2. Find a transaction date at the beginning of the line.
        # ---------------------------------------------------------
        date_match = re.match(
            r"^(\d{4}[-/]\d{2}[-/]\d{2})\b",
            line,
        )

        if not date_match:
            continue

        date_value = date_match.group(1)

        remainder = line[date_match.end():].strip()

        # ---------------------------------------------------------
        # 3. Find the final monetary amount on the line.
        #
        # Example:
        # UPI-NETFLIX ENTERTAINMENT ... UPI 649.00
        # ---------------------------------------------------------
        amount_matches = list(
            re.finditer(
                r"(?<!\w)(?:₹\s*)?[0-9][0-9,]*(?:\.[0-9]{1,2})?(?!\w)",
                remainder,
            )
        )

        if not amount_matches:
            continue

        amount_match = amount_matches[-1]

        amount_value = amount_match.group(0)

        # Remove rupee symbol and commas.
        amount_value = (
            amount_value
            .replace("₹", "")
            .replace(",", "")
            .strip()
        )

        try:
            float(amount_value)
        except ValueError:
            continue

        # ---------------------------------------------------------
        # 4. Everything before the amount is the narration.
        # ---------------------------------------------------------
        description = remainder[:amount_match.start()].strip()

        if not description:
            continue

        # ---------------------------------------------------------
        # 5. Remove a trailing currency marker if OCR included it.
        # ---------------------------------------------------------
        currency = "INR"

        currency_match = re.search(
            r"\b(INR|₹|RS\.?|RUPEES)\s*$",
            description,
            re.IGNORECASE,
        )

        if currency_match:
            description = description[:currency_match.start()].strip()

        # ---------------------------------------------------------
        # 6. If the amount is followed by a currency marker,
        #    recognize it.
        # ---------------------------------------------------------
        after_amount = remainder[amount_match.end():].strip()

        trailing_currency = re.match(
            r"^(INR|USD|EUR|GBP|₹|RS\.?|RUPEES)\b",
            after_amount,
            re.IGNORECASE,
        )

        if trailing_currency:
            detected_currency = trailing_currency.group(1).upper()

            if detected_currency in {"₹", "RS.", "RUPEES"}:
                currency = "INR"
            else:
                currency = detected_currency

        # ---------------------------------------------------------
        # 7. Avoid accidentally treating column headers as rows.
        # ---------------------------------------------------------
        if description.lower() in {
            "date",
            "description",
            "amount",
            "currency",
            "narration",
        }:
            continue

        rows.append(
            {
                "date": date_value,
                "amount": amount_value,
                "currency": currency,
                "raw_description": description,
            }
        )

    return rows


def parse_statement(
    source: str | Path | bytes | BinaryIO,
    filename: str | None = None,
) -> pd.DataFrame:
    """
    Choose the local parser based on the statement file type.
    """
    name = (filename or str(source)).lower()

    if name.endswith(".csv"):
        return parse_csv(source)

    if name.endswith(".pdf"):
        return parse_pdf(source)

    raise ValueError(
        "Unsupported statement format. Please provide a CSV or PDF."
    )


def _table_to_rows(
    table: list[list[str | None]],
) -> list[dict]:
    """
    Convert a structured PDF table into transaction dictionaries.

    Supports common bank-statement column aliases.
    """
    if not table or not table[0]:
        return []

    aliases = {
        "transaction_date": "date",
        "txn_date": "date",

        "description": "raw_description",
        "transaction_description": "raw_description",
        "narration": "raw_description",
        "particulars": "raw_description",
        "merchant": "raw_description",

        "transaction_amount": "amount",
        "amount_(debit)": "amount",
        "debit": "amount",
        "withdrawal": "amount",
        "withdrawal_amt": "amount",

        "credit": "amount",
        "deposit": "amount",
        "deposit_amt": "amount",

        "curr": "currency",
    }

    header = [
        re.sub(
            r"\W+",
            "_",
            str(cell or "").strip().lower(),
        ).strip("_")
        for cell in table[0]
    ]

    normalized_header = [
        aliases.get(column, column)
        for column in header
    ]

    # Currency is optional for structured bank PDFs because
    # many Indian statements encode INR in the column header.
    required = {
        "date",
        "amount",
        "raw_description",
    }

    if not required.issubset(set(normalized_header)):
        return []

    rows = []

    for raw_row in table[1:]:
        if not raw_row:
            continue

        row = {}

        for index, value in enumerate(raw_row):
            if index >= len(normalized_header):
                continue

            column = normalized_header[index]

            if column not in {
                "date",
                "amount",
                "currency",
                "raw_description",
            }:
                continue

            if value is None:
                continue

            cleaned = str(value).strip()

            if cleaned:
                row[column] = cleaned

        if (
            row.get("date")
            and row.get("amount")
            and row.get("raw_description")
        ):
            row.setdefault("currency", "INR")
            rows.append(row)

    return rows


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize parser output without changing ChargeLens's
    existing downstream architecture.
    """
    df = df.copy()

    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            "Parsed statement is missing required columns: "
            f"{sorted(missing)}"
        )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce",
    )

    df["currency"] = (
        df["currency"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["raw_description"] = (
        df["raw_description"]
        .astype(str)
        .str.strip()
    )

    df = df.dropna(
        subset=[
            "date",
            "amount",
        ]
    )

    df = df[
        [
            "date",
            "amount",
            "currency",
            "raw_description",
        ]
    ].reset_index(drop=True)

    return df