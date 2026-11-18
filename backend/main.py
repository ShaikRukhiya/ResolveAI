import json
import logging
import os
import re
import sqlite3
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from dotenv import dotenv_values, load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
DEFAULT_SARVAM_MODEL = "sarvam-105b-conversations"
load_dotenv(ENV_FILE)
logger = logging.getLogger(__name__)


def get_sarvam_api_key() -> str:
    environment_key = os.getenv("SARVAM_API_KEY", "").strip()
    if environment_key:
        return environment_key
    file_key = dotenv_values(ENV_FILE).get("SARVAM_API_KEY", "")
    return file_key.strip() if isinstance(file_key, str) else ""


logger.info("Backend environment file: %s", ENV_FILE)
logger.info("SARVAM_API_KEY detected: %s", bool(get_sarvam_api_key()))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "resolveai.db")))
LANGUAGES = {
    "en-IN": "English",
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
}
COMPLAINT_STATUSES = {
    "received": ("Complaint Received", "Your complaint was registered in this demo. No real support team has been contacted."),
    "details_being_checked": ("Details Being Checked", "The submitted information is being validated in this demo record."),
    "action_required": ("Action Required", "Additional information is needed to continue. Check the update note for what to provide."),
    "resolution_update": ("Resolution Update", "A demo outcome or recommended next step is available in the update note."),
    "resolved": ("Resolved", "This demo complaint has been marked resolved. This does not represent a real-world resolution."),
}
COMPLAINT_TRANSITIONS = {
    "received": {"details_being_checked"},
    "details_being_checked": {"action_required", "resolution_update"},
    "action_required": {"details_being_checked", "resolution_update"},
    "resolution_update": {"action_required", "resolved"},
    "resolved": set(),
}
INTENT_TERMS = {
    "debited_not_received": [
        "money debited", "amount debited", "debited but", "charged but", "paid but",
        "merchant did not receive", "merchant hasn't received", "merchant has not received",
        "not received the money", "receiver didn't get", "debited not received",
        "पैसे कट", "पैसा कट", "कट गए", "मर्चेंट को नहीं", "दुकानदार को नहीं मिला",
        "பணம் கழ", "பணம் பிடித்தம்", "வணிகருக்கு வரவில்லை", "கடை கிடைக்க",
        "డబ్బు కట్", "డెబిట్ అయింది", "డబ్బు డెబిట్", "వ్యాపారికి అందలేదు", "మర్చంట్ అంద",
    ],
    "double_payment": [
        "paid twice", "charged twice", "double charged", "double payment", "duplicate payment",
        "two payments", "twice for", "दो बार", "दो बार पैसे", "डबल पेमेंट", "இரண்டு முறை",
        "இரண்டு தடவை", "రెండు సార్లు", "రెండుసార్లు", "డబుల్ పేమెంట్",
    ],
    "refund_timeline": [
        "how long", "when will", "when can", "how many days", "refund take", "refund time",
        "refund arrive", "refund timeline", "कितने दिन", "कब तक", "రిఫండ్ ఎప్పుడు",
        "ఎన్ని రోజులు", "எத்தனை நாள்", "எப்போது வரும்", "எவ்வளவு நேரம்",
    ],
    "refund_status": [
        "refund", "refunded", "money back", "return my money", "where is my",
        "रिफंड", "वापस", "திருப்பி", "ரீஃபண்ட்", "రిఫండ్", "వాపస్",
    ],
    "payment_failed": [
        "payment failed", "payment fail", "failed payment", "transaction failed", "failure",
        "declined", "fail", "failed", "भुगतान विफल", "पेमेंट फेल", "पेमेंट असफल",
        "தோல்வி", "பணம் செலுத்த முடிய", "చెల్లింపు విఫల", "పేమెంట్ ఫెయిల్",
    ],
    "pending_status": [
        "pending", "still processing", "waiting for confirmation", "not completed yet",
        "पेंडिंग", "लंबित", "நிலுவை", "காத்திருக்க", "పెండింగ్", "వేచి",
    ],
    "complaint": [
        "complaint", "raise a complaint", "file a complaint", "dispute", "report this",
        "शिकायत", "புகார்", "ఫిర్యాదు", "కంప్లైంట్",
    ],
    "next_steps": [
        "what should i do", "what do i do", "what next", "next step", "help me",
        "how can i resolve", "क्या करूं", "क्या करना", "आगे क्या", "என்ன செய்ய",
        "அடுத்து என்ன", "ఏం చేయాలి", "తర్వాత ఏమి",
    ],
    "transaction_status": [
        "transaction status", "payment status", "status of", "check status",
        "मेरी पेमेंट का स्टेटस", "भुगतान की स्थिति", "பரிவர்த்தனை நிலை",
        "చెల్లింపు స్థితి",
    ],
}
app = FastAPI(title="ResolveAI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS",
            os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173"),
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database():
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with database() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL REFERENCES customers(id),
                merchant TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'INR',
                payment_method TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('successful', 'pending', 'failed')),
                created_at TEXT NOT NULL,
                bank_reference TEXT,
                description TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS complaints (
                id TEXT PRIMARY KEY,
                transaction_id TEXT REFERENCES transactions(id),
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS complaint_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id TEXT NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                explanation TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS refunds (
                id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL UNIQUE REFERENCES transactions(id),
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expected_by TEXT
            );
            CREATE TABLE IF NOT EXISTS support_information (
                status TEXT PRIMARY KEY,
                explanation TEXT NOT NULL,
                next_step TEXT NOT NULL
            );
            """
        )
        db.execute(
            "INSERT OR IGNORE INTO customers (id, display_name) VALUES (?, ?)",
            ("demo-customer", "Rukhiya"),
        )
        db.execute(
            "UPDATE customers SET display_name = 'Rukhiya' WHERE id = 'demo-customer'"
        )
        db.execute(
            "UPDATE complaints SET status = 'received' WHERE status = 'under_review'"
        )
        db.execute(
            """UPDATE complaints SET status = 'received'
            WHERE status = 'details_being_checked' AND EXISTS (
                SELECT 1 FROM complaint_status_history
                WHERE complaint_status_history.complaint_id = complaints.id
                AND complaint_status_history.explanation = ?
            )""",
            ("Legacy demo status; no real support review is implied.",),
        )
        db.execute(
            """UPDATE complaint_status_history
            SET status = 'received', explanation = ?
            WHERE status = 'details_being_checked' AND explanation = ?""",
            (
                "Legacy complaint migrated as received; no real support review is implied.",
                "Legacy demo status; no real support review is implied.",
            ),
        )
        db.execute(
            """INSERT INTO complaint_status_history (complaint_id, status, explanation, created_at)
            SELECT complaints.id, complaints.status, ?, complaints.created_at
            FROM complaints
            WHERE NOT EXISTS (
                SELECT 1 FROM complaint_status_history
                WHERE complaint_status_history.complaint_id = complaints.id
            )""",
            ("Legacy complaint migrated as received; no real support review is implied.",),
        )
        existing = db.execute("SELECT COUNT(*) AS count FROM transactions").fetchone()["count"]
        if not existing:
            now = utc_now()
            sample = [
                ("TXN-482913", "Blue Tokai Coffee", 485, "UPI", "successful", 0, "Paid via UPI", "UPI240915482913"),
                ("TXN-482876", "Metro Recharge", 300, "UPI", "pending", 1, "Mobile recharge", "UPI240914482876"),
                ("TXN-482801", "FreshBasket", 1249, "UPI", "failed", 2, "Grocery order payment", "UPI240913482801"),
                ("TXN-482744", "Myntra", 2199, "Paytm Wallet", "successful", 3, "Fashion purchase", "WAL240912482744"),
                ("TXN-482690", "Swiggy", 642, "UPI", "successful", 4, "Food order payment", "UPI240911482690"),
                ("TXN-482611", "BookMyShow", 899, "UPI", "pending", 5, "Movie tickets", "UPI240910482611"),
                ("TXN-482530", "Airtel Broadband", 999, "UPI", "successful", 6, "Monthly broadband bill", "UPI240909482530"),
                ("TXN-482441", "Urban Company", 1599, "UPI", "failed", 7, "Home service payment", "UPI240908482441"),
            ]
            for ref, merchant, amount, method, status, days_ago, description, bank_ref in sample:
                created = (now - timedelta(days=days_ago, hours=2)).isoformat()
                db.execute(
                    """INSERT INTO transactions
                    (id, customer_id, merchant, amount, payment_method, status, created_at, bank_reference, description)
                    VALUES (?, 'demo-customer', ?, ?, ?, ?, ?, ?, ?)""",
                    (ref, merchant, amount, method, status, created, bank_ref, description),
                )
            for ref, amount, status, age in (
                ("TXN-482801", 1249, "processing", 1),
                ("TXN-482441", 1599, "initiated", 2),
            ):
                updated = (now - timedelta(hours=age * 6)).isoformat()
                expected = (now + timedelta(days=3)).date().isoformat()
                db.execute(
                    """INSERT INTO refunds (id, transaction_id, amount, status, updated_at, expected_by)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    ("RFD-" + ref[-6:], ref, amount, status, updated, expected),
                )
            for status, explanation, next_step in (
                ("successful", "The payment is marked successful in this demo record.", "If the merchant has not confirmed it, share the transaction reference with them."),
                ("pending", "The payment is still being confirmed by the payment network.", "Wait for the status to update before retrying. You can check again later."),
                ("failed", "The demo record shows that this payment did not complete.", "If an amount was debited, check the refund tracker for its return progress."),
            ):
                db.execute(
                    "INSERT OR IGNORE INTO support_information VALUES (?, ?, ?)",
                    (status, explanation, next_step),
                )


def transaction_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def complaint_dict(row: sqlite3.Row) -> dict:
    result = dict(row)
    current_index = list(COMPLAINT_STATUSES).index(result["status"])
    history = result.pop("history")
    latest_update = history[-1] if history else None
    result["status_label"] = COMPLAINT_STATUSES[result["status"]][0]
    result["status_explanation"] = (
        latest_update["explanation"]
        if latest_update and latest_update["status"] == result["status"]
        else COMPLAINT_STATUSES[result["status"]][1]
    )
    result["status_history"] = history
    result["timeline"] = [
        {
            "status": item["status"],
            "label": COMPLAINT_STATUSES[item["status"]][0],
            "explanation": item["explanation"],
            "at": item["created_at"],
            "complete": True,
            "current": index == len(history) - 1,
            "skipped": False,
        }
        for index, item in enumerate(history)
    ]
    recorded_statuses = {item["status"] for item in history}
    result["timeline"].extend(
        {
            "status": status,
            "label": details[0],
            "explanation": details[1],
            "at": None,
            "complete": False,
            "current": False,
            "skipped": index < current_index,
        }
        for index, (status, details) in enumerate(COMPLAINT_STATUSES.items())
        if status not in recorded_statuses
    )
    result["is_demo"] = True
    return result


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/api/health")
def health():
    with database() as db:
        db.execute("SELECT 1").fetchone()
    return {"status": "ok", "database": "connected"}


@app.get("/api/transactions")
def list_transactions(
    status: Literal["successful", "pending", "failed"] | None = None,
    search: str = Query(default="", max_length=80),
):
    clauses, values = [], []
    if status:
        clauses.append("status = ?")
        values.append(status)
    if search.strip():
        term = f"%{search.strip()}%"
        clauses.append("(id LIKE ? OR merchant LIKE ? OR description LIKE ?)")
        values.extend((term, term, term))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with database() as db:
        rows = db.execute(
            f"SELECT * FROM transactions {where} ORDER BY created_at DESC", values
        ).fetchall()
    return [transaction_dict(row) for row in rows]


@app.get("/api/transactions/{transaction_id}")
def get_transaction(transaction_id: str):
    with database() as db:
        row = db.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transaction not found")
        refund = db.execute(
            "SELECT * FROM refunds WHERE transaction_id = ?", (transaction_id,)
        ).fetchone()
        support = db.execute(
            "SELECT * FROM support_information WHERE status = ?", (row["status"],)
        ).fetchone()
    result = transaction_dict(row)
    result["refund"] = dict(refund) if refund else None
    result["resolution_guidance"] = dict(support)
    result["timeline"] = [
        {"label": "Payment initiated", "at": row["created_at"], "complete": True},
        {"label": "Bank confirmation", "at": row["created_at"] if row["status"] == "successful" else None, "complete": row["status"] == "successful"},
        {"label": "Payment complete", "at": row["created_at"] if row["status"] == "successful" else None, "complete": row["status"] == "successful"},
    ]
    return result


@app.get("/api/refunds")
def list_refunds():
    with database() as db:
        rows = db.execute(
            """SELECT refunds.*, transactions.merchant, transactions.created_at AS transaction_date
            FROM refunds JOIN transactions ON transactions.id = refunds.transaction_id
            ORDER BY refunds.updated_at DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/refunds/{transaction_id}")
def get_refund(transaction_id: str):
    with database() as db:
        row = db.execute(
            """SELECT refunds.*, transactions.merchant, transactions.created_at AS transaction_date
            FROM refunds JOIN transactions ON transactions.id = refunds.transaction_id
            WHERE refunds.transaction_id = ? OR refunds.id = ?""",
            (transaction_id, transaction_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No refund record found for this reference")
    return dict(row)


class ComplaintCreate(BaseModel):
    transaction_id: str | None = Field(default=None, max_length=32)
    category: str = Field(min_length=3, max_length=60)
    description: str = Field(min_length=10, max_length=1000)


@app.post("/api/complaints", status_code=201)
def create_complaint(payload: ComplaintCreate):
    with database() as db:
        if payload.transaction_id:
            exists = db.execute(
                "SELECT 1 FROM transactions WHERE id = ?", (payload.transaction_id,)
            ).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Selected transaction was not found")
        complaint_id = "CMP-" + uuid4().hex[:8].upper()
        created_at = utc_now().isoformat()
        explanation = COMPLAINT_STATUSES["received"][1]
        db.execute(
            """INSERT INTO complaints (id, transaction_id, category, description, status, created_at)
            VALUES (?, ?, ?, ?, 'received', ?)""",
            (complaint_id, payload.transaction_id, payload.category.strip(), payload.description.strip(), created_at),
        )
        db.execute(
            """INSERT INTO complaint_status_history (complaint_id, status, explanation, created_at)
            VALUES (?, 'received', ?, ?)""",
            (complaint_id, explanation, created_at),
        )
        complaint = load_complaint(db, complaint_id)
    return complaint_dict(complaint)


def load_complaint(db: sqlite3.Connection, complaint_id: str) -> dict | None:
    row = db.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["history"] = [
        dict(item)
        for item in db.execute(
            """SELECT status, explanation, created_at FROM complaint_status_history
            WHERE complaint_id = ? ORDER BY id""",
            (complaint_id,),
        ).fetchall()
    ]
    return result


@app.get("/api/complaints")
def list_complaints():
    with database() as db:
        rows = db.execute("SELECT id FROM complaints ORDER BY created_at DESC").fetchall()
        complaints = [load_complaint(db, row["id"]) for row in rows]
    return [complaint_dict(complaint) for complaint in complaints]


class ComplaintStatusUpdate(BaseModel):
    status: Literal[
        "received",
        "details_being_checked",
        "action_required",
        "resolution_update",
        "resolved",
    ]
    explanation: str | None = Field(default=None, min_length=5, max_length=500)


@app.patch("/api/complaints/{complaint_id}/status")
def update_complaint_status(complaint_id: str, payload: ComplaintStatusUpdate):
    normalized_id = complaint_id.upper()
    with database() as db:
        complaint = load_complaint(db, normalized_id)
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found")
        current_status = complaint["status"]
        if payload.status not in COMPLAINT_TRANSITIONS[current_status]:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot move complaint from {COMPLAINT_STATUSES[current_status][0]} to {COMPLAINT_STATUSES[payload.status][0]}",
            )
        updated_at = utc_now().isoformat()
        explanation = (payload.explanation or COMPLAINT_STATUSES[payload.status][1]).strip()
        db.execute(
            "UPDATE complaints SET status = ? WHERE id = ?",
            (payload.status, normalized_id),
        )
        db.execute(
            """INSERT INTO complaint_status_history (complaint_id, status, explanation, created_at)
            VALUES (?, ?, ?, ?)""",
            (normalized_id, payload.status, explanation, updated_at),
        )
        updated = load_complaint(db, normalized_id)
    return complaint_dict(updated)


@app.get("/api/complaints/{complaint_id}")
def get_complaint(complaint_id: str):
    with database() as db:
        complaint = load_complaint(db, complaint_id.upper())
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint_dict(complaint)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1500)
    language: Literal["en-IN", "hi-IN", "ta-IN", "te-IN"] = "en-IN"
    transaction_id: str | None = Field(default=None, max_length=32)
    history: list["ChatTurn"] = Field(default_factory=list, max_length=12)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1500)
    language: Literal["en-IN", "hi-IN", "ta-IN", "te-IN"] = "en-IN"


ChatRequest.model_rebuild()


def detect_intent(message: str) -> str:
    normalized = message.casefold().strip()
    scores = {
        intent: sum(
            1
            for term in terms
            if (
                re.search(rf"(?<!\w){re.escape(term)}(?!\w)", normalized)
                if term.isascii()
                else term in normalized
            )
        )
        for intent, terms in INTENT_TERMS.items()
    }
    # Specific payment problems take priority over broader refund/next-step wording.
    priorities = {
        "debited_not_received": 9,
        "double_payment": 8,
        "refund_timeline": 7,
        "refund_status": 6,
        "payment_failed": 5,
        "pending_status": 4,
        "complaint": 3,
        "next_steps": 2,
        "transaction_status": 1,
    }
    best = max(scores, key=lambda intent: (scores[intent], priorities[intent]))
    return best if scores[best] else "unknown"


def find_transaction(message: str, selected_id: str | None) -> sqlite3.Row | None:
    with database() as db:
        if selected_id:
            row = db.execute("SELECT * FROM transactions WHERE id = ?", (selected_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Selected transaction was not found")
            return row
        reference = re.search(r"\b(?:TXN|UPI|WAL|RFD)[- ]?[A-Z0-9]{5,}\b", message, re.IGNORECASE)
        if reference:
            normalized = reference.group(0).replace(" ", "").upper()
            if normalized.startswith("RFD"):
                row = db.execute(
                    """SELECT transactions.* FROM refunds
                    JOIN transactions ON transactions.id = refunds.transaction_id
                    WHERE UPPER(refunds.id) = ?""",
                    (normalized,),
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT * FROM transactions WHERE UPPER(id) = ? OR UPPER(bank_reference) = ?",
                    (normalized, normalized),
                ).fetchone()
            if row:
                return row
        merchant_rows = db.execute(
            "SELECT * FROM transactions ORDER BY created_at DESC"
        ).fetchall()
        lowered = message.casefold()
        matches = [
            row for row in merchant_rows
            if row["merchant"].casefold() in lowered
        ]
        if len(matches) == 1:
            return matches[0]
        amounts = re.findall(
            r"(?:₹|INR\s*)\s*([\d,]+(?:\.\d{1,2})?)", message, re.IGNORECASE
        )
        if amounts:
            amount = float(amounts[0].replace(",", ""))
            matches = db.execute(
                "SELECT * FROM transactions WHERE amount = ? ORDER BY created_at DESC",
                (amount,),
            ).fetchall()
            if len(matches) == 1:
                return matches[0]
    return None


def get_transaction_context(transaction: sqlite3.Row | None) -> dict | None:
    if transaction is None:
        return None
    with database() as db:
        refund = db.execute(
            "SELECT id, amount, status, updated_at, expected_by FROM refunds WHERE transaction_id = ?",
            (transaction["id"],),
        ).fetchone()
    return {
        "id": transaction["id"],
        "merchant": transaction["merchant"],
        "amount": transaction["amount"],
        "currency": transaction["currency"],
        "payment_method": transaction["payment_method"],
        "status": transaction["status"],
        "created_at": transaction["created_at"],
        "description": transaction["description"],
        "refund": dict(refund) if refund else None,
    }


def is_short_follow_up(message: str) -> bool:
    normalized = message.casefold().strip()
    if normalized in {
        "and then", "what now", "what next", "why", "how", "when", "and?", "then?",
        "अब?", "फिर?", "அப்புறம்?", "తర్వాత?",
    }:
        return True
    return len(normalized.split()) <= 3 and not re.search(r"\b(?:refund|complaint|pending|failed|failure)\b", normalized)


def effective_intent(payload: ChatRequest) -> str:
    intent = detect_intent(payload.message)
    if intent != "unknown":
        return intent
    if payload.history and is_short_follow_up(payload.message):
        for turn in reversed(payload.history):
            if turn.role == "user":
                previous_intent = detect_intent(turn.content)
                if previous_intent != "unknown":
                    return previous_intent
    return "unknown"


def local_answer(
    intent: str,
    transaction: sqlite3.Row | None,
    previous_intent: str = "unknown",
) -> tuple[str, bool]:
    if intent == "unknown":
        return (
            "Could you share a little more? Tell me whether this is about a failed or pending payment, "
            "a debit the merchant did not receive, a refund, or a duplicate charge. Include a transaction "
            "reference or merchant and date if you have one.",
            True,
        )
    if transaction is None and intent == "pending_status":
        return (
            "Pending means a payment is awaiting confirmation; it does not prove that your specific "
            "payment is pending. I couldn't match a transaction, so I can't verify its status. "
            "Check the selected transaction or share its reference before retrying.",
            True,
        )
    if transaction is None and intent == "payment_failed":
        return (
            "I couldn't match a transaction, so I can't tell why this payment failed. Failures can "
            "have different causes; check the status in the app, avoid retrying until you know whether "
            "it was recorded, and share the transaction reference so I can check the demo record.",
            True,
        )
    if transaction is None and intent in {
        "debited_not_received", "refund_status", "refund_timeline", "next_steps",
        "transaction_status",
    }:
        return (
            "I can explain the next steps, but I couldn't match your question to a demo transaction. "
            "No payment or refund status is verified. Choose a transaction above, or share its demo "
            "reference, merchant, and approximate date.",
            True,
        )
    if intent == "double_payment":
        return (
            "I can't confirm a duplicate from the records available here. Compare both transaction "
            "references and amounts in Transactions. If both entries show successful, keep both "
            "references and raise a complaint; avoid retrying until you confirm whether a second "
            "payment was actually recorded.",
            False,
        )
    if intent == "complaint":
        return (
            "You can register a complaint from Complaints: choose a category, optionally link a "
            "transaction, describe what happened, and save the generated reference to track its "
            "demo status. No real support team is contacted by this prototype.",
            False,
        )
    if transaction is None:
        return (
            "I can help with that. Select a transaction or include its reference so I can check the "
            "available demo record before giving transaction-specific guidance.",
            True,
        )

    record = get_transaction_context(transaction)
    status = record["status"]
    refund = record["refund"]
    prefix = (
        f"For the simulated record {record['id']} at {record['merchant']} "
        f"({money_text(record['amount'])}), the recorded payment status is {status}. "
    )
    if intent in {"refund_status", "refund_timeline"}:
        if not refund:
            return (
                prefix + "I don't have a refund record linked to this payment, so I can't verify "
                "whether or when money will return. Check Refunds again when a record is available, "
                "or raise a complaint if an amount was debited.",
                False,
            )
        timing = (
            f"The demo record lists an estimated date of {refund['expected_by']}."
            if refund["expected_by"]
            else "No estimated completion date is recorded."
        )
        return (
            prefix + f"The linked demo refund {refund['id']} is recorded as {refund['status']}. "
            + timing + " This is not a bank-confirmed date or guarantee. Use Track a refund for updates.",
            False,
        )
    if intent == "pending_status":
        if status == "pending":
            return (
                prefix + "Pending means the payment is awaiting confirmation in this demo record. "
                "Check again later before retrying, and confirm with the merchant using the transaction "
                "reference if needed.",
                False,
            )
        return (
            prefix + "This record is not pending. If your app shows something different, share the "
            "current reference or check again later; I can't verify live bank or merchant systems.",
            False,
        )
    if intent == "payment_failed":
        if status == "failed":
            if refund:
                return (
                    prefix + f"The linked demo refund is {refund['status']} ({refund['id']}). "
                    "Check Refunds for its available progress. A failed payment record does not itself "
                    "prove that a debit was reversed.",
                    False,
                )
            return (
                prefix + "If money was debited, I don't see a linked refund record here. Check your "
                "bank statement and raise a complaint with this transaction reference if the debit "
                "remains. This demo cannot verify a bank reversal.",
                False,
            )
        return (
            prefix + "This record is not marked failed. If the merchant says otherwise, compare the "
            "transaction reference with them and raise a complaint if the mismatch continues.",
            False,
        )
    if intent == "debited_not_received":
        if status == "failed":
            if refund:
                return (
                    prefix + f"The linked demo refund is recorded as {refund['status']}. Check its "
                    f"reference {refund['id']} in Refunds. I can't confirm whether your bank has "
                    "credited the amount.",
                    False,
                )
            return (
                prefix + "No linked refund is recorded. Check your statement and share this reference "
                "with the merchant; if the debit remains, raise a complaint. I can't confirm a bank "
                "credit from this demo.",
                False,
            )
        if status == "pending":
            return (
                prefix + "The record is awaiting confirmation. Don't retry yet; check the status later "
                "and share the reference with the merchant if they still cannot see it.",
                False,
            )
        return (
            prefix + "A successful record does not confirm that the merchant has matched the payment. "
            "Share the transaction reference with the merchant and raise a complaint if they still "
            "cannot locate it.",
            False,
        )
    if intent == "next_steps":
        if status == "failed":
            if refund and refund["status"] == "processed":
                next_action = f"check your statement for the linked refund {refund['id']}, which is marked processed in this demo"
            elif refund:
                next_action = f"check the linked refund {refund['id']} ({refund['status']})"
            else:
                next_action = "check your statement for a debit and raise a complaint if it remains"
        elif status == "pending":
            next_action = "wait for confirmation, then check the status before trying again"
        else:
            next_action = "share the transaction reference with the merchant if they cannot locate the payment"
        return prefix + f"Next: {next_action}. This demo cannot check live bank or merchant systems.", False
    if intent == "transaction_status":
        if refund and refund["status"] == "processed":
            return (
                prefix + f"The linked demo refund {refund['id']} is marked processed. That refund "
                "status is separate from the payment status and does not confirm a bank credit.",
                False,
            )
        if refund:
            return (
                prefix + f"The linked demo refund {refund['id']} is recorded as {refund['status']}. "
                "A refund record is separate from the payment status.",
                False,
            )
        return prefix + "I don't see a linked refund record. This is simulated data, not a live check.", False
    return prefix + "This is simulated data, not a live Paytm or bank check.", False


def money_text(amount: float) -> str:
    return f"₹{amount:,.2f}"


def sarvam_answer(
    payload: ChatRequest,
    intent: str,
    transaction: sqlite3.Row | None,
) -> tuple[str, str, bool]:
    context = get_transaction_context(transaction)
    if context is None:
        context_text = "No transaction could be matched. Do not infer a payment, refund, or bank status."
    else:
        context_text = json.dumps(context, ensure_ascii=False)
    system = (
        "You are ResolveAI, a careful financial-journey support assistant. First identify the user's "
        "intent, then answer concisely and empathetically in " + LANGUAGES[payload.language] + ". "
        "Return only a JSON object with keys intent, answer, needs_clarification. The intent must be "
        "one of: debited_not_received, double_payment, refund_timeline, refund_status, payment_failed, "
        "pending_status, complaint, next_steps, transaction_status, unknown. Use the user's words and "
        "conversation history for intent and follow-ups, but only the supplied transaction JSON is "
        "verified. It is simulated prototype data, never live Paytm/bank data. Never invent statuses, "
        "refund dates, bank confirmations, complaint progress, or promises. If a necessary reference, "
        "date, amount, or other fact is missing, ask one focused clarification question. For refunds, "
        "distinguish no refund record from an initiated/processing record and only state expected_by "
        "if present. For a debit/merchant issue, do not claim the merchant received money merely from "
        "a successful status. Give practical numbered steps when useful. Never request an OTP, PIN, "
        "password, or full bank/card number. Context: " + context_text + ". "
        "Local intent signal (may be corrected by understanding the full conversation): " + intent
    )
    messages = [{"role": "system", "content": system}]
    messages.extend(
        {
            "role": turn.role,
            "content": f"[Original language: {LANGUAGES[turn.language]}] {turn.content}",
        }
        for turn in payload.history[-10:]
    )
    messages.append({"role": "user", "content": payload.message})
    body = {
        "model": os.getenv("SARVAM_MODEL", DEFAULT_SARVAM_MODEL).strip() or DEFAULT_SARVAM_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 400,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        "https://api.sarvam.ai/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"api-subscription-key": get_sarvam_api_key(), "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        response_data = json.loads(response.read().decode("utf-8"))
    content = response_data["choices"][0]["message"]["content"].strip()
    parsed = json.loads(content)
    answer = parsed["answer"]
    model_intent = parsed.get("intent", intent)
    needs_clarification = parsed.get("needs_clarification", False)
    allowed_intents = {*INTENT_TERMS, "transaction_status", "unknown"}
    if (
        not isinstance(answer, str)
        or not answer.strip()
        or model_intent not in allowed_intents
        or not isinstance(needs_clarification, bool)
    ):
        raise ValueError("Sarvam returned an invalid assistant response")
    return answer.strip(), model_intent, needs_clarification


@app.post("/api/assistant/chat")
def chat(payload: ChatRequest):
    intent = effective_intent(payload)
    api_key = get_sarvam_api_key()
    context_id = payload.transaction_id
    if not context_id:
        reference = re.search(r"\b(?:TXN|UPI|WAL)[- ]?[A-Z0-9]{5,}\b", payload.message, re.IGNORECASE)
        if not reference:
            for turn in reversed(payload.history):
                if turn.role == "assistant":
                    previous_reference = re.search(
                        r"\bTXN-[A-Z0-9]{5,}\b", turn.content, re.IGNORECASE
                    )
                    if previous_reference:
                        context_id = previous_reference.group(0).upper()
                        break
    transaction = find_transaction(payload.message, context_id)
    if api_key:
        try:
            answer, model_intent, needs_clarification = sarvam_answer(
                payload, intent, transaction
            )
            fallback = False
        except (
            urllib.error.URLError,
            OSError,
            TimeoutError,
            KeyError,
            IndexError,
            TypeError,
            AttributeError,
            ValueError,
        ) as error:
            answer, needs_clarification = local_answer(intent, transaction)
            model_intent = intent
            fallback = True
            http_status = getattr(error, "code", None)
            logger.warning(
                "Sarvam request failed; api_key_present=%s; error_type=%s; http_status=%s",
                bool(api_key),
                type(error).__name__,
                http_status,
            )
            fallback_reason = (
                f"Sarvam returned HTTP {http_status}."
                if http_status
                else f"Sarvam request failed ({type(error).__name__})."
            )
    else:
        answer, needs_clarification = local_answer(intent, transaction)
        model_intent = intent
        fallback = True
        fallback_reason = "SARVAM_API_KEY is not configured."
    fallback_message = None
    if fallback:
        fallback_message = (
            f"{fallback_reason} Showing English demo guidance, not an AI-generated answer or translation."
        )
    return {
        "answer": answer,
        "language": payload.language,
        "transaction": get_transaction_context(transaction),
        "mode": "demo_fallback" if fallback else "sarvam",
        "fallback": fallback,
        "fallback_message": fallback_message,
        "intent": model_intent,
        "needs_clarification": needs_clarification,
    }
