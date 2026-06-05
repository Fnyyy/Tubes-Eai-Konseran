import os
import time

from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel, Field


MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "venue")

app = FastAPI(title="Venue Service", version="1.0.0")
mongo_client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
database = mongo_client[MONGODB_DB]
capacity_collection = database["venue_capacity"]
reservations = database["reservations"]


class ReservationRequest(BaseModel):
    order_id: str
    concert_id: str = Field(examples=["concert-2026-jkt"])
    ticket_type: str
    quantity: int = Field(gt=0)


def init_db() -> None:
    for attempt in range(12):
        try:
            mongo_client.admin.command("ping")
            break
        except Exception:
            if attempt == 11:
                raise
            time.sleep(2)
    capacity_collection.create_index([("concert_id", 1), ("ticket_type", 1)], unique=True)
    reservations.create_index("order_id", unique=True)
    for item in [
        {"concert_id": "concert-2026-jkt", "ticket_type": "REGULAR", "capacity": 500, "reserved": 0},
        {"concert_id": "concert-2026-jkt", "ticket_type": "VIP", "capacity": 80, "reserved": 0},
    ]:
        capacity_collection.update_one(
            {"concert_id": item["concert_id"], "ticket_type": item["ticket_type"]},
            {"$setOnInsert": item},
            upsert=True,
        )


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "venue"}


@app.get("/capacity/{concert_id}")
def capacity(concert_id: str) -> list[dict]:
    rows = capacity_collection.find({"concert_id": concert_id}, {"_id": 0})
    return list(rows)


@app.post("/reservations", status_code=201)
def reserve(request: ReservationRequest) -> dict:
    existing = reservations.find_one({"order_id": request.order_id}, {"_id": 0})
    if existing:
        return {"status": "ALREADY_RESERVED", **existing}

    row = capacity_collection.find_one(
        {"concert_id": request.concert_id, "ticket_type": request.ticket_type}
    )
    if not row:
        raise HTTPException(status_code=404, detail="Concert or ticket type not found")

    available = row["capacity"] - row["reserved"]
    if available < request.quantity:
        raise HTTPException(status_code=409, detail="Insufficient venue capacity")

    capacity_collection.update_one(
        {"concert_id": request.concert_id, "ticket_type": request.ticket_type},
        {"$inc": {"reserved": request.quantity}},
    )
    reservation = {
        "order_id": request.order_id,
        "concert_id": request.concert_id,
        "ticket_type": request.ticket_type,
        "quantity": request.quantity,
    }
    reservations.insert_one(reservation)
    return {"status": "RESERVED", **reservation}
