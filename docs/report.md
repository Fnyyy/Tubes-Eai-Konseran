# Laporan Singkat Proyek Akhir EAI

## 1. Tema dan Tujuan

Tema proyek adalah integrasi sistem Concert Organizer yang terdiri dari Ticketing, Venue, Artist/Lineup, Payment, dan Notification. Masalah yang disimulasikan adalah information silo: tiap aplikasi memiliki database dan format data sendiri, sehingga proses pembelian tiket perlu diintegrasikan lewat lapisan integrasi.

Tujuan sistem adalah membuat satu event bisnis dari Ticketing dapat memicu proses otomatis ke Venue, Payment, Artist/Lineup, dan Notification tanpa akses database lintas service.

## 2. Arsitektur Integrasi

Arsitektur memakai microservices dan RabbitMQ. Ticketing Service menerbitkan event `ticket.order.created`. Integration Worker menjadi lapisan integrasi yang mengonsumsi event, memanggil adapter REST ke Venue, Payment, Artist, dan Ticketing, lalu menerbitkan event notifikasi.

Setiap service memiliki MongoDB sendiri yang disimpan dalam Docker volume terpisah. RabbitMQ juga memakai volume agar queue dan metadata broker tetap persisten saat container restart.

## 3. Gaya Integrasi

Gaya integrasi utama adalah messaging asinkron melalui RabbitMQ untuk event bisnis, digabung dengan API-led integration sinkron melalui REST untuk operasi yang membutuhkan respons langsung, seperti reservasi venue dan pembayaran.

Kombinasi ini dipilih karena event order cocok diproses asinkron, sementara langkah reservasi dan pembayaran membutuhkan validasi sukses/gagal sebelum order dikonfirmasi.

## 4. Enterprise Integration Patterns

Pola yang diterapkan:

- Message Channel: exchange `concert.events` dan queue `integration.ticket-order`, `notification.participant`.
- Message Endpoint/Adapter: Integration Worker menjadi endpoint RabbitMQ dan adapter REST ke service lain.
- Message Translator: data lineup dari Artist Service berbentuk XML diubah menjadi JSON internal.
- Content-Based Router: channel notifikasi ditentukan dari tipe tiket, `VIP` menjadi `sms`, `REGULAR` menjadi `email`.
- Canonical Data Model: semua event internal memakai envelope `event_id`, `event_type`, `occurred_at`, `source`, dan `data`.
- Dead Letter Channel: pesan gagal setelah retry masuk ke `concert.events.dlx`.

## 5. Mapping dan Transformasi Data

Ticketing menerbitkan event canonical JSON. Artist Service sengaja menyediakan endpoint XML:

```xml
<lineup concertId="concert-2026-jkt">
  <artist>
    <name>Nadin Amizah</name>
    <stage>Main Stage</stage>
    <startTime>19:00</startTime>
  </artist>
</lineup>
```

Integration Worker mengubahnya menjadi JSON:

```json
[
  {
    "name": "Nadin Amizah",
    "stage": "Main Stage",
    "start_time": "19:00"
  }
]
```

Hasil transformasi dipakai untuk membuat pesan notifikasi peserta.

## 6. Alur End-to-End

1. Peserta membuat order tiket melalui Ticketing Service.
2. Ticketing menyimpan order `PENDING` dan publish event `ticket.order.created`.
3. Integration Worker consume event.
4. Worker membuat reservasi ke Venue Service.
5. Worker membuat pembayaran ke Payment Service.
6. Worker mengambil lineup XML dari Artist Service dan melakukan transformasi ke JSON.
7. Worker mengubah status order di Ticketing menjadi `CONFIRMED` jika pembayaran sukses.
8. Worker menerbitkan event notifikasi.
9. Notification Service menyimpan notifikasi ke database sendiri.

## 7. Ketahanan

Retry diterapkan di Integration Worker menggunakan header `retry_count`. Jika sudah melebihi `MAX_RETRIES`, pesan dikirim ke dead-letter exchange. Notification Service memakai `event_id` sebagai primary key dan `INSERT OR IGNORE` untuk mencegah duplikasi notifikasi saat event terkirim ulang.

## 8. Kendala dan Solusi

Kendala utama adalah menjaga agar demo tetap ringan tetapi memenuhi heterogenitas data dan EIP. Solusinya adalah memakai MongoDB per service untuk database mandiri, RabbitMQ sebagai broker, dan XML khusus pada Artist Service agar transformasi format dapat ditunjukkan jelas.

## 9. Pembagian Tugas

Isi bagian ini sesuai anggota kelompok:

- Anggota 1: arsitektur integrasi dan Ticketing.
- Anggota 2: Venue, Payment, dan Artist/Lineup.
- Anggota 3: Notification, Docker Compose, dokumentasi, dan demo.
