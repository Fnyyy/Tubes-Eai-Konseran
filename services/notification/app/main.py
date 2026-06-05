import json
import os
import threading
import time

import pika
from fastapi import FastAPI
from pymongo import MongoClient


MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "notification")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = os.getenv("EXCHANGE_NAME", "concert.events")
DLX_NAME = os.getenv("DLX_NAME", "concert.events.dlx")
NOTIFICATION_QUEUE = os.getenv("NOTIFICATION_QUEUE", "notification.participant")
NOTIFICATION_ROUTING_KEY = os.getenv("NOTIFICATION_ROUTING_KEY", "notification.participant.created")

app = FastAPI(title="Notification Service", version="1.0.0")
mongo_client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
notifications = mongo_client[MONGODB_DB]["notifications"]


def init_db() -> None:
    for attempt in range(12):
        try:
            mongo_client.admin.command("ping")
            break
        except Exception:
            if attempt == 11:
                raise
            time.sleep(2)
    notifications.create_index("created_at")


def consume_notifications() -> None:
    params = pika.URLParameters(RABBITMQ_URL)
    while True:
        try:
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
            channel.exchange_declare(exchange=DLX_NAME, exchange_type="topic", durable=True)
            channel.queue_declare(
                queue=NOTIFICATION_QUEUE,
                durable=True,
                arguments={"x-dead-letter-exchange": DLX_NAME},
            )
            channel.queue_bind(
                exchange=EXCHANGE_NAME,
                queue=NOTIFICATION_QUEUE,
                routing_key=NOTIFICATION_ROUTING_KEY,
            )
            channel.basic_qos(prefetch_count=1)

            def on_message(ch, method, properties, body):
                payload = json.loads(body.decode("utf-8"))
                data = payload["data"]
                notifications.update_one(
                    {"_id": payload["event_id"]},
                    {
                        "$setOnInsert": {
                            "order_id": data["order_id"],
                            "participant_email": data["participant_email"],
                            "channel": data["channel"],
                            "subject": data["subject"],
                            "message": data["message"],
                            "created_at": payload["occurred_at"],
                        }
                    },
                    upsert=True,
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_consume(queue=NOTIFICATION_QUEUE, on_message_callback=on_message)
            channel.start_consuming()
        except Exception:
            time.sleep(3)


@app.on_event("startup")
def startup() -> None:
    init_db()
    thread = threading.Thread(target=consume_notifications, daemon=True)
    thread.start()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "notification"}


@app.get("/notifications")
def list_notifications() -> list[dict]:
    rows = notifications.find().sort("created_at", -1)
    result = []
    for row in rows:
        row["event_id"] = str(row.pop("_id"))
        result.append(row)
    return result
