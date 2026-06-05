import json
import os
import time
import uuid
from decimal import Decimal
from typing import Literal

import pika
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel, EmailStr, Field


MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "ticketing")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = os.getenv("EXCHANGE_NAME", "concert.events")
ORDER_CREATED_ROUTING_KEY = os.getenv("ORDER_CREATED_ROUTING_KEY", "ticket.order.created")

app = FastAPI(title="Ticketing Service", version="1.0.0")
mongo_client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
orders = mongo_client[MONGODB_DB]["orders"]


class OrderCreate(BaseModel):
    concert_id: str = Field(examples=["concert-2026-jkt"])
    participant_name: str = Field(examples=["Rani Putri"])
    participant_email: EmailStr = Field(examples=["rani@example.com"])
    ticket_type: Literal["REGULAR", "VIP"] = "REGULAR"
    quantity: int = Field(gt=0, le=10, examples=[2])
    amount: Decimal = Field(gt=0, examples=["750000"])
    currency: str = Field(default="IDR", min_length=3, max_length=3)
    payment_method: Literal["CARD", "BANK_TRANSFER", "EWALLET"] = "EWALLET"


class StatusUpdate(BaseModel):
    status: Literal["PENDING", "CONFIRMED", "FAILED"]
    payment_status: Literal["WAITING", "PAID", "FAILED"] | None = None
    failure_reason: str | None = None


def init_db() -> None:
    for attempt in range(12):
        try:
            mongo_client.admin.command("ping")
            break
        except Exception:
            if attempt == 11:
                raise
            time.sleep(2)
    orders.create_index("created_at")


def publish_event(payload: dict) -> None:
    params = pika.URLParameters(RABBITMQ_URL)
    for attempt in range(10):
        try:
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
            channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=ORDER_CREATED_ROUTING_KEY,
                body=json.dumps(payload).encode("utf-8"),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                    message_id=payload["event_id"],
                    timestamp=int(time.time()),
                ),
            )
            connection.close()
            return
        except pika.exceptions.AMQPConnectionError:
            if attempt == 9:
                raise
            time.sleep(2)


def serialize(document: dict) -> dict:
    document["id"] = str(document.pop("_id"))
    return document


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ticketing"}


@app.post("/orders", status_code=201)
def create_order(request: OrderCreate) -> dict:
    order_id = str(uuid.uuid4())
    created_at = int(time.time())
    orders.insert_one(
        {
            "_id": order_id,
            "concert_id": request.concert_id,
            "participant_name": request.participant_name,
            "participant_email": request.participant_email,
            "ticket_type": request.ticket_type,
            "quantity": request.quantity,
            "amount": str(request.amount),
            "currency": request.currency,
            "payment_method": request.payment_method,
            "status": "PENDING",
            "payment_status": "WAITING",
            "failure_reason": None,
            "created_at": created_at,
        }
    )

    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "TicketOrderCreated",
        "occurred_at": created_at,
        "source": "ticketing-service",
        "data": {
            "order_id": order_id,
            "concert_id": request.concert_id,
            "customer": {
                "name": request.participant_name,
                "email": request.participant_email,
            },
            "ticket": {
                "type": request.ticket_type,
                "quantity": request.quantity,
            },
            "payment": {
                "amount": str(request.amount),
                "currency": request.currency,
                "method": request.payment_method,
            },
        },
    }
    publish_event(event)
    return {"order_id": order_id, "status": "PENDING", "event": event}


@app.get("/orders")
def list_orders() -> list[dict]:
    return [serialize(row) for row in orders.find().sort("created_at", -1)]


@app.get("/orders/{order_id}")
def get_order(order_id: str) -> dict:
    row = orders.find_one({"_id": order_id})
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize(row)


@app.patch("/orders/{order_id}/status")
def update_status(order_id: str, request: StatusUpdate) -> dict:
    update = {
        "status": request.status,
        "failure_reason": request.failure_reason,
    }
    if request.payment_status:
        update["payment_status"] = request.payment_status

    row = orders.find_one_and_update(
        {"_id": order_id},
        {"$set": update},
        return_document=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize(row)
