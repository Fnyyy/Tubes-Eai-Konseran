# Demo Script

Durasi target: 5-10 menit.

## 1. Jalankan Sistem

```bash
docker compose up --build
```

Tunjukkan container aktif dan RabbitMQ Management UI di http://localhost:15672.

## 2. Tunjukkan OpenAPI

Buka:

- http://localhost:8001/docs
- http://localhost:8002/docs
- http://localhost:8003/docs
- http://localhost:8004/docs
- http://localhost:8005/docs

## 3. Buat Order

```bash
curl -X POST http://localhost:8001/orders \
  -H "Content-Type: application/json" \
  -d '{
    "concert_id": "concert-2026-jkt",
    "participant_name": "Rani Putri",
    "participant_email": "rani@example.com",
    "ticket_type": "VIP",
    "quantity": 2,
    "amount": "1500000",
    "currency": "IDR",
    "payment_method": "EWALLET"
  }'
```

Jelaskan bahwa Ticketing tidak memanggil database service lain, hanya publish event.

## 4. Validasi Efek Integrasi

```bash
curl http://localhost:8001/orders
curl http://localhost:8002/capacity/concert-2026-jkt
curl http://localhost:8004/payments
curl http://localhost:8005/notifications
```

Tunjukkan status order `CONFIRMED`, kapasitas venue bertambah di kolom `reserved`, payment `PAID`, dan notifikasi tersimpan.

## 5. Tunjukkan Heterogenitas

```bash
curl http://localhost:8003/lineup/concert-2026-jkt.xml
```

Jelaskan bahwa Integration Worker melakukan XML-to-JSON translator sebelum membuat pesan notifikasi.
