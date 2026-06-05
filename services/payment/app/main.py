import os
import time
import uuid
from decimal import Decimal
from typing import Literal

from fastapi import FastAPI
from pymongo import MongoClient
from pydantic import BaseModel, Field


MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "payment")

app = FastAPI(title="Payment Service", version="1.0.0")
mongo_client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
payments = mongo_client[MONGODB_DB]["payments"]


class PaymentRequest(BaseModel):
    order_id: str
    amount: Decimal = Field(gt=0)
    currency: str = "IDR"
    method: Literal["CARD", "BANK_TRANSFER", "EWALLET"] = "EWALLET"


def init_db() -> None:
    for attempt in range(12):
        try:
            mongo_client.admin.command("ping")
            break
        except Exception:
            if attempt == 11:
                raise
            time.sleep(2)
    payments.create_index("order_id", unique=True)


def serialize(document: dict) -> dict:
    document["id"] = str(document.pop("_id"))
    return document


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "payment"}


@app.post("/payments", status_code=201)
def create_payment(request: PaymentRequest) -> dict:
    existing = payments.find_one({"order_id": request.order_id})
    if existing:
        return serialize(existing)

    status = "FAILED" if request.method == "BANK_TRANSFER" and request.amount > 5000000 else "PAID"
    payment = {
        "_id": str(uuid.uuid4()),
        "order_id": request.order_id,
        "amount": str(request.amount),
        "currency": request.currency,
        "method": request.method,
        "status": status,
    }
    payments.insert_one(payment)
    return serialize(payment)


@app.get("/payments")
def list_payments() -> list[dict]:
    return [serialize(row) for row in payments.find()]
