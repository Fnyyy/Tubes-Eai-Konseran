import json
import os
import time
import uuid
import xml.etree.ElementTree as ET

import pika
import requests


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = os.getenv("EXCHANGE_NAME", "concert.events")
DLX_NAME = os.getenv("DLX_NAME", "concert.events.dlx")
ORDER_QUEUE = os.getenv("ORDER_QUEUE", "integration.ticket-order")
ORDER_CREATED_ROUTING_KEY = os.getenv("ORDER_CREATED_ROUTING_KEY", "ticket.order.created")
NOTIFICATION_ROUTING_KEY = os.getenv("NOTIFICATION_ROUTING_KEY", "notification.participant.created")
VENUE_URL = os.getenv("VENUE_URL", "http://localhost:8002")
ARTIST_URL = os.getenv("ARTIST_URL", "http://localhost:8003")
PAYMENT_URL = os.getenv("PAYMENT_URL", "http://localhost:8004")
TICKETING_URL = os.getenv("TICKETING_URL", "http://localhost:8001")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


def setup_channel():
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=DLX_NAME, exchange_type="topic", durable=True)
    channel.queue_declare(
        queue=ORDER_QUEUE,
        durable=True,
        arguments={"x-dead-letter-exchange": DLX_NAME},
    )
    channel.queue_bind(
        exchange=EXCHANGE_NAME,
        queue=ORDER_QUEUE,
        routing_key=ORDER_CREATED_ROUTING_KEY,
    )
    channel.basic_qos(prefetch_count=1)
    return connection, channel


def translate_lineup_xml(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    return [
        {
            "name": artist.findtext("name"),
            "stage": artist.findtext("stage"),
            "start_time": artist.findtext("startTime"),
        }
        for artist in root.findall("artist")
    ]


def update_ticket(order_id: str, status: str, payment_status: str, failure_reason: str | None = None) -> None:
    requests.patch(
        f"{TICKETING_URL}/orders/{order_id}/status",
        json={
            "status": status,
            "payment_status": payment_status,
            "failure_reason": failure_reason,
        },
        timeout=10,
    ).raise_for_status()


def build_notification(order_event: dict, payment: dict, lineup: list[dict]) -> dict:
    data = order_event["data"]
    first_artist = lineup[0]["name"] if lineup else "our opening act"
    channel = "sms" if data["ticket"]["type"] == "VIP" else "email"
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "ParticipantNotificationRequested",
        "occurred_at": int(time.time()),
        "source": "integration-worker",
        "data": {
            "order_id": data["order_id"],
            "participant_email": data["customer"]["email"],
            "channel": channel,
            "subject": "Concert ticket confirmed",
            "message": (
                f"Hi {data['customer']['name']}, your {data['ticket']['quantity']} "
                f"{data['ticket']['type']} ticket(s) are confirmed. "
                f"Payment {payment['status']}. Lineup starts with {first_artist}."
            ),
        },
    }


def publish_notification(channel, payload: dict) -> None:
    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=NOTIFICATION_ROUTING_KEY,
        body=json.dumps(payload).encode("utf-8"),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
            message_id=payload["event_id"],
            timestamp=payload["occurred_at"],
        ),
    )


def process_order(channel, order_event: dict) -> None:
    data = order_event["data"]
    order_id = data["order_id"]

    requests.post(
        f"{VENUE_URL}/reservations",
        json={
            "order_id": order_id,
            "concert_id": data["concert_id"],
            "ticket_type": data["ticket"]["type"],
            "quantity": data["ticket"]["quantity"],
        },
        timeout=10,
    ).raise_for_status()

    payment = requests.post(
        f"{PAYMENT_URL}/payments",
        json={
            "order_id": order_id,
            "amount": data["payment"]["amount"],
            "currency": data["payment"]["currency"],
            "method": data["payment"]["method"],
        },
        timeout=10,
    ).json()

    if payment["status"] != "PAID":
        update_ticket(order_id, "FAILED", "FAILED", "Payment rejected by payment service")
        return

    lineup_xml = requests.get(f"{ARTIST_URL}/lineup/{data['concert_id']}.xml", timeout=10).text
    lineup = translate_lineup_xml(lineup_xml)
    update_ticket(order_id, "CONFIRMED", "PAID")
    publish_notification(channel, build_notification(order_event, payment, lineup))


def should_retry(properties) -> bool:
    headers = properties.headers or {}
    retry_count = int(headers.get("retry_count", 0))
    return retry_count < MAX_RETRIES


def retry_message(channel, method, properties, body) -> None:
    headers = properties.headers or {}
    retry_count = int(headers.get("retry_count", 0)) + 1
    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=method.routing_key,
        body=body,
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
            headers={"retry_count": retry_count},
        ),
    )


def main() -> None:
    while True:
        try:
            connection, channel = setup_channel()

            def on_message(ch, method, properties, body):
                try:
                    event = json.loads(body.decode("utf-8"))
                    process_order(ch, event)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception:
                    if should_retry(properties):
                        retry_message(ch, method, properties, body)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_consume(queue=ORDER_QUEUE, on_message_callback=on_message)
            print("Integration worker is consuming ticket.order.created events", flush=True)
            channel.start_consuming()
            connection.close()
        except Exception as exc:
            print(f"Worker reconnecting after error: {exc}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
