# import os
# import re
# import json
# import logging
# from datetime import datetime
# from typing import Optional

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from openai import OpenAI

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("invoice-extractor")

# # ---------------------------------------------------------------------------
# # App setup
# # ---------------------------------------------------------------------------

# app = FastAPI(title="Invoice Extraction API")

# # CORS: grader calls from a Cloudflare Worker, so allow all origins.
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=False,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # LLM client (AIPIPE proxy). Reads OPENAI_API_KEY / OPENAI_BASE_URL from env.
# OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
# LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

# client: Optional[OpenAI] = None
# if OPENAI_API_KEY:
#     client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


# class ExtractRequest(BaseModel):
#     invoice_text: str


# REQUIRED_KEYS = ["invoice_no", "date", "vendor", "amount", "tax", "currency"]


# def empty_result():
#     return {k: None for k in REQUIRED_KEYS}


# # ---------------------------------------------------------------------------
# # Regex-based extraction
# # ---------------------------------------------------------------------------

# MONTHS = {
#     "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
#     "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
#     "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
#     "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
# }


# def normalize_date(raw: str) -> Optional[str]:
#     raw = raw.strip().strip(",")
#     # Try ISO already
#     m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", raw)
#     if m:
#         return raw

#     # DD Month YYYY  e.g. "15 March 2026"
#     m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", raw)
#     if m:
#         day, mon, year = m.groups()
#         mon_num = MONTHS.get(mon.lower())
#         if mon_num:
#             return f"{int(year):04d}-{mon_num:02d}-{int(day):02d}"

#     # Month DD, YYYY  e.g. "March 15, 2026"
#     m = re.match(r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$", raw)
#     if m:
#         mon, day, year = m.groups()
#         mon_num = MONTHS.get(mon.lower())
#         if mon_num:
#             return f"{int(year):04d}-{mon_num:02d}-{int(day):02d}"

#     # DD/MM/YYYY or DD-MM-YYYY
#     m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", raw)
#     if m:
#         day, mon, year = m.groups()
#         try:
#             return f"{int(year):04d}-{int(mon):02d}-{int(day):02d}"
#         except ValueError:
#             return None

#     # YYYY/MM/DD
#     m = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$", raw)
#     if m:
#         year, mon, day = m.groups()
#         return f"{int(year):04d}-{int(mon):02d}-{int(day):02d}"

#     return None


# def parse_number(raw: str) -> Optional[float]:
#     if raw is None:
#         return None
#     cleaned = raw.replace(",", "").strip()
#     try:
#         return float(cleaned)
#     except ValueError:
#         return None


# def regex_extract(text: str) -> dict:
#     result = empty_result()

#     # invoice_no
#     m = re.search(r"Invoice\s*(?:No|Number|#)\.?\s*[:\-]?\s*([A-Za-z0-9\-\/]+)", text, re.I)
#     if m:
#         result["invoice_no"] = m.group(1).strip()

#     # date
#     m = re.search(r"\bDate\s*[:\-]?\s*([0-9]{1,4}[\/\-][A-Za-z0-9]+[\/\-][0-9]{1,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})", text, re.I)
#     if m:
#         result["date"] = normalize_date(m.group(1))

#     # vendor
#     m = re.search(r"Vendor\s*[:\-]?\s*(.+)", text, re.I)
#     if m:
#         vendor_line = m.group(1).strip()
#         # cut off if it accidentally grabbed the next field on same line
#         vendor_line = re.split(r"\s{2,}|(?=Subtotal|Sub Total|GST|Tax|TOTAL)", vendor_line, flags=re.I)[0]
#         result["vendor"] = vendor_line.strip().rstrip(".,")

#     # amount (subtotal, before tax)
#     m = re.search(r"Sub\s*[- ]?\s*[Tt]otal\s*[:\-]?\s*(?:Rs\.?|INR|₹|\$)?\s*([\d,]+\.?\d*)", text, re.I)
#     if m:
#         result["amount"] = parse_number(m.group(1))

#     # tax
#     m = re.search(r"(?:GST|Tax|VAT)\s*(?:\(\s*\d+\s*%\s*\))?\s*[:\-]?\s*(?:Rs\.?|INR|₹|\$)?\s*([\d,]+\.?\d*)", text, re.I)
#     if m:
#         result["tax"] = parse_number(m.group(1))

#     # currency
#     if re.search(r"Rs\.?|INR|₹", text):
#         result["currency"] = "INR"
#     elif re.search(r"\$|USD", text):
#         result["currency"] = "USD"
#     elif re.search(r"€|EUR", text):
#         result["currency"] = "EUR"
#     elif re.search(r"£|GBP", text):
#         result["currency"] = "GBP"

#     return result


# def missing_fields(result: dict):
#     return [k for k in REQUIRED_KEYS if result.get(k) in (None, "")]


# # ---------------------------------------------------------------------------
# # LLM fallback extraction (via AIPIPE / OpenAI-compatible proxy)
# # ---------------------------------------------------------------------------

# LLM_SYSTEM_PROMPT = """You extract structured data from raw invoice text.
# Return ONLY a JSON object with exactly these 6 keys, no other text, no markdown fences:

# {
#   "invoice_no": string or null,
#   "date": string in YYYY-MM-DD format or null,
#   "vendor": string or null,
#   "amount": number or null,   // subtotal BEFORE tax, not the grand total
#   "tax": number or null,      // tax amount only (e.g. GST/VAT amount)
#   "currency": string or null  // 3-letter ISO code e.g. INR, USD, EUR
# }

# Rules:
# - amount is the pre-tax subtotal, never the total-after-tax.
# - date must always be normalized to YYYY-MM-DD.
# - If a field cannot be determined, use null.
# - Output must be valid JSON and nothing else.
# """


# def llm_extract(text: str, existing: dict) -> dict:
#     if client is None:
#         logger.warning("LLM client not configured (missing OPENAI_API_KEY); skipping fallback.")
#         return existing

#     try:
#         response = client.chat.completions.create(
#             model=LLM_MODEL,
#             messages=[
#                 {"role": "system", "content": LLM_SYSTEM_PROMPT},
#                 {"role": "user", "content": f"Invoice text:\n---\n{text}\n---"},
#             ],
#             temperature=0,
#         )
#         raw = response.choices[0].message.content.strip()

#         # Strip accidental markdown fences
#         raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())

#         parsed = json.loads(raw)

#         merged = dict(existing)
#         for key in REQUIRED_KEYS:
#             if merged.get(key) in (None, "") and parsed.get(key) not in (None, ""):
#                 merged[key] = parsed[key]

#         # normalize date/number types coming back from the LLM
#         if merged.get("date"):
#             normalized = normalize_date(str(merged["date"]))
#             merged["date"] = normalized if normalized else merged["date"]
#         if merged.get("amount") is not None:
#             try:
#                 merged["amount"] = float(merged["amount"])
#             except (TypeError, ValueError):
#                 pass
#         if merged.get("tax") is not None:
#             try:
#                 merged["tax"] = float(merged["tax"])
#             except (TypeError, ValueError):
#                 pass

#         return merged

#     except Exception as e:
#         logger.exception("LLM extraction failed: %s", e)
#         return existing


# # ---------------------------------------------------------------------------
# # Routes
# # ---------------------------------------------------------------------------

# @app.get("/")
# def root():
#     return {"status": "ok", "service": "invoice-extraction-api"}


# @app.get("/health")
# def health():
#     return {"status": "healthy", "llm_configured": client is not None}


# @app.post("/extract")
# def extract(req: ExtractRequest):
#     text = req.invoice_text or ""

#     result = regex_extract(text)

#     # If anything important is still missing, fall back to the LLM.
#     if missing_fields(result):
#         result = llm_extract(text, result)

#     # Final safety net: ensure all 6 keys exist even if something went wrong.
#     final = empty_result()
#     final.update({k: result.get(k) for k in REQUIRED_KEYS})

#     return final


import os
import re
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("invoice-extractor")

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Invoice Extraction API")

# CORS: grader calls from a Cloudflare Worker, so allow all origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LLM client (AIPIPE proxy). Reads OPENAI_API_KEY / OPENAI_BASE_URL from env.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

client: Optional[OpenAI] = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    except Exception as e:
        # Never let a bad client init take down the whole app on boot.
        logger.exception("Failed to initialize OpenAI client: %s", e)
        client = None


class ExtractRequest(BaseModel):
    invoice_text: str


REQUIRED_KEYS = ["invoice_no", "date", "vendor", "amount", "tax", "currency"]


def empty_result():
    return {k: None for k in REQUIRED_KEYS}


# ---------------------------------------------------------------------------
# Regex-based extraction
# ---------------------------------------------------------------------------

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def normalize_date(raw: str) -> Optional[str]:
    raw = raw.strip().strip(",")
    # Try ISO already
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", raw)
    if m:
        return raw

    # DD Month YYYY  e.g. "15 March 2026"
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", raw)
    if m:
        day, mon, year = m.groups()
        mon_num = MONTHS.get(mon.lower())
        if mon_num:
            return f"{int(year):04d}-{mon_num:02d}-{int(day):02d}"

    # Month DD, YYYY  e.g. "March 15, 2026"
    m = re.match(r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$", raw)
    if m:
        mon, day, year = m.groups()
        mon_num = MONTHS.get(mon.lower())
        if mon_num:
            return f"{int(year):04d}-{mon_num:02d}-{int(day):02d}"

    # DD/MM/YYYY or DD-MM-YYYY
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", raw)
    if m:
        day, mon, year = m.groups()
        try:
            return f"{int(year):04d}-{int(mon):02d}-{int(day):02d}"
        except ValueError:
            return None

    # YYYY/MM/DD
    m = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$", raw)
    if m:
        year, mon, day = m.groups()
        return f"{int(year):04d}-{int(mon):02d}-{int(day):02d}"

    return None


def parse_number(raw: str) -> Optional[float]:
    if raw is None:
        return None
    cleaned = raw.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def regex_extract(text: str) -> dict:
    result = empty_result()

    # invoice_no
    m = re.search(r"Invoice\s*(?:No|Number|#)\.?\s*[:\-]?\s*([A-Za-z0-9\-\/]+)", text, re.I)
    if m:
        result["invoice_no"] = m.group(1).strip()

    # date
    m = re.search(r"\bDate\s*[:\-]?\s*([0-9]{1,4}[\/\-][A-Za-z0-9]+[\/\-][0-9]{1,4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})", text, re.I)
    if m:
        result["date"] = normalize_date(m.group(1))

    # vendor
    m = re.search(r"Vendor\s*[:\-]?\s*(.+)", text, re.I)
    if m:
        vendor_line = m.group(1).strip()
        # cut off if it accidentally grabbed the next field on same line
        vendor_line = re.split(r"\s{2,}|(?=Subtotal|Sub Total|GST|Tax|TOTAL)", vendor_line, flags=re.I)[0]
        result["vendor"] = vendor_line.strip().rstrip(".,")

    # amount (subtotal, before tax)
    m = re.search(r"Sub\s*[- ]?\s*[Tt]otal\s*[:\-]?\s*(?:Rs\.?|INR|₹|\$)?\s*([\d,]+\.?\d*)", text, re.I)
    if m:
        result["amount"] = parse_number(m.group(1))

    # tax — this is the trickiest field. Strategy:
    # 1. Find every "money-looking" number on a line that mentions a tax keyword.
    # 2. Explicitly SKIP numbers immediately followed by '%' (those are rates, not amounts).
    # 3. If multiple tax lines exist (CGST + SGST etc.), sum them.
    TAX_KEYWORDS = r"(?:GST|IGST|CGST|SGST|UTGST|VAT|Tax(?:\s*Amount)?)"
    NUMBER = r"[\d,]+\.?\d*"

    tax_total = None
    tax_line_found = False

    for line in text.splitlines():
        if not re.search(TAX_KEYWORDS, line, re.I):
            continue
        tax_line_found = True

        # Remove any "N%" or "(N%)" chunks so they can never be mistaken for the amount.
        cleaned_line = re.sub(r"\(?\s*\d+\.?\d*\s*%\s*\)?", " ", line)

        # Now find money-like numbers in what's left, preferring ones near a currency symbol.
        money_matches = re.findall(
            r"(?:Rs\.?|INR|₹|\$|USD|€|EUR|£|GBP)\s*(" + NUMBER + r")|(" + NUMBER + r")\s*(?:Rs\.?|INR|₹|\$)?",
            cleaned_line,
            re.I,
        )
        # Flatten tuples, drop empties
        candidates = [g1 or g2 for g1, g2 in money_matches if (g1 or g2)]
        # Drop tiny non-numeric leftovers (e.g. stray commas) and require actual digits
        candidates = [c for c in candidates if re.search(r"\d", c)]

        if candidates:
            # Take the last/most specific numeric match on the line (closest to line end,
            # typically the actual amount rather than a code/number earlier in the label).
            val = parse_number(candidates[-1])
            if val is not None:
                tax_total = (tax_total or 0) + val

    if tax_line_found and tax_total is not None:
        result["tax"] = round(tax_total, 2)

    # currency
    if re.search(r"Rs\.?|INR|₹", text):
        result["currency"] = "INR"
    elif re.search(r"\$|USD", text):
        result["currency"] = "USD"
    elif re.search(r"€|EUR", text):
        result["currency"] = "EUR"
    elif re.search(r"£|GBP", text):
        result["currency"] = "GBP"

    return result


def missing_fields(result: dict):
    return [k for k in REQUIRED_KEYS if result.get(k) in (None, "")]


# ---------------------------------------------------------------------------
# LLM fallback extraction (via AIPIPE / OpenAI-compatible proxy)
# ---------------------------------------------------------------------------

LLM_SYSTEM_PROMPT = """You extract structured data from raw invoice text.
Return ONLY a JSON object with exactly these 6 keys, no other text, no markdown fences:

{
  "invoice_no": string or null,
  "date": string in YYYY-MM-DD format or null,
  "vendor": string or null,
  "amount": number or null,   // subtotal BEFORE tax, not the grand total
  "tax": number or null,      // tax amount only (e.g. GST/VAT amount)
  "currency": string or null  // 3-letter ISO code e.g. INR, USD, EUR
}

Rules:
- amount is the pre-tax subtotal, never the total-after-tax.
- tax is the actual currency amount of tax charged — NEVER the percentage rate.
  For example if you see "GST (18%): Rs. 395.82", tax = 395.82, NOT 18.
- If tax is split across multiple lines (e.g. CGST + SGST, or IGST + UTGST),
  sum all of them into a single tax value.
- date must always be normalized to YYYY-MM-DD.
- If a field cannot be determined, use null.
- Output must be valid JSON and nothing else.
"""


def llm_extract(text: str, existing: dict) -> dict:
    if client is None:
        logger.warning("LLM client not configured (missing OPENAI_API_KEY); skipping fallback.")
        return existing

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": f"Invoice text:\n---\n{text}\n---"},
            ],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()

        # Strip accidental markdown fences
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())

        parsed = json.loads(raw)

        merged = dict(existing)
        for key in REQUIRED_KEYS:
            if merged.get(key) in (None, "") and parsed.get(key) not in (None, ""):
                merged[key] = parsed[key]

        # normalize date/number types coming back from the LLM
        if merged.get("date"):
            normalized = normalize_date(str(merged["date"]))
            merged["date"] = normalized if normalized else merged["date"]
        if merged.get("amount") is not None:
            try:
                merged["amount"] = float(merged["amount"])
            except (TypeError, ValueError):
                pass
        if merged.get("tax") is not None:
            try:
                merged["tax"] = float(merged["tax"])
            except (TypeError, ValueError):
                pass

        return merged

    except Exception as e:
        logger.exception("LLM extraction failed: %s", e)
        return existing


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "ok", "service": "invoice-extraction-api"}


@app.get("/health")
def health():
    return {"status": "healthy", "llm_configured": client is not None}


@app.post("/extract")
def extract(req: ExtractRequest):
    text = req.invoice_text or ""

    result = regex_extract(text)

    # If anything important is still missing, fall back to the LLM.
    if missing_fields(result):
        result = llm_extract(text, result)

    # Final safety net: ensure all 6 keys exist even if something went wrong.
    final = empty_result()
    final.update({k: result.get(k) for k in REQUIRED_KEYS})

    return final