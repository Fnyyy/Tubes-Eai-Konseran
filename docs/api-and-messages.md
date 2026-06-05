# API And Message Documentation

## Ticketing Service

### `POST /orders`

Request:

```json
{
  "concert_id": "concert-2026-jkt",
  "participant_name": "Rani Putri",
  "participant_email": "rani@example.com",
  "ticket_type": "VIP",
  "quantity": 2,
  "amount": "1500000",
  "currency": "IDR",
  "payment_method": "EWALLET"
}
```

Response:

```json
{
  "order_id": "uuid",
  "status": "PENDING",
  "event": {
    "event_id": "uuid",
    "event_type": "TicketOrderCreated"
  }
}
```

### `PATCH /orders/{order_id}/status`

Dipakai oleh integration worker untuk update hasil proses lintas sistem.

```json
{
  "status": "CONFIRMED",
  "payment_status": "PAID",
  "failure_reason": null
}
```

## Venue Service

### `POST /reservations`

```json
{
  "order_id": "uuid",
  "concert_id": "concert-2026-jkt",
  "ticket_type": "VIP",
  "quantity": 2
}
```

## Artist Lineup Service

### `GET /lineup/{concert_id}.xml`

Mengembalikan XML untuk memenuhi heterogenitas format.

```xml
<lineup concertId="concert-2026-jkt">
  <artist>
    <name>Nadin Amizah</name>
    <stage>Main Stage</stage>
    <startTime>19:00</startTime>
  </artist>
</lineup>
```

## Payment Service

### `POST /payments`

```json
{
  "order_id": "uuid",
  "amount": "1500000",
  "currency": "IDR",
  "method": "EWALLET"
}
```

## Notification Event

Routing key: `notification.participant.created`

```json
{
  "event_id": "uuid",
  "event_type": "ParticipantNotificationRequested",
  "occurred_at": 1767229200,
  "source": "integration-worker",
  "data": {
    "order_id": "uuid",
    "participant_email": "rani@example.com",
    "channel": "sms",
    "subject": "Concert ticket confirmed",
    "message": "Hi Rani Putri, your 2 VIP ticket(s) are confirmed."
  }
}
```
