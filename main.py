from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceIn(BaseModel):
    invoice_text: str

def parse_date(text):
    m = re.search(r'Date:\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})', text)
    if not m:
        return None
    return datetime.strptime(m.group(1), "%d %B %Y").strftime("%Y-%m-%d")

def money_to_float(s):
    return float(s.replace(",", "").replace("Rs.", "").replace("Rs", "").strip())

@app.post("/extract")
async def extract(payload: InvoiceIn):
    text = payload.invoice_text

    invoice_no = re.search(r'Invoice No:\s*(.+)', text)
    vendor = re.search(r'Vendor:\s*(.+)', text)
    subtotal = re.search(r'Subtotal:\s*Rs\.\s*([0-9,]+\.\d{2})', text)
    gst = re.search(r'GST\s*\(\d+%\):\s*Rs\.\s*([0-9,]+\.\d{2})', text)
    date = parse_date(text)

    return {
        "invoice_no": invoice_no.group(1).strip() if invoice_no else None,
        "date": date,
        "vendor": vendor.group(1).strip() if vendor else None,
        "amount": money_to_float(subtotal.group(1)) if subtotal else None,
        "tax": money_to_float(gst.group(1)) if gst else None,
        "currency": "INR",
    }