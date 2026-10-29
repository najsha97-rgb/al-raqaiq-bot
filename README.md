# Panduan Pemasangan & Pengoperasian Bot Telegram Al-Raqaiq (الرقائق)

Bot Telegram pintar untuk rujukan pantas kitab **Al-Raqā'iq (Pelembut-pelembut Hati)** karya As-Syeikh Muhammad Ahmad ar-Rasyid *rahimahullah*.

---

## 🚀 Langkah 1: Dapatkan Token Bot dari @BotFather

1. Buka aplikasi Telegram dan cari **@BotFather**.
2. Hantar arahan `/newbot`.
3. Berikan nama untuk bot (contoh: `Al-Raqaiq Pelembut Hati`).
4. Berikan username bot (contoh: `RaqaiqKu_bot` atau `AlRaqaiq_bot`).
5. Salin token API yang diberikan (contoh: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

---

## ⚙️ Langkah 2: Masukkan Token ke Dalam `config.json`

Buka fail `config.json` dan gantikan:
```json
{
  "bot_token": "MASUKKAN_TOKEN_TELEGRAM_DI_SINI",
  "bot_name": "RaqaiqKu_bot",
  "description": "Bot Rasmi Pelembut-pelembut Hati Al-Raqaiq"
}
```

---

## 🏃 Langkah 3: Menjalankan Bot

Pastikan Python telah dipasang, kemudian jalankan arahan:
```bash
pip install -r requirements.txt
python bot.py
```
Atau klik dua kali pada fail `start_bot.bat`.

---

## 📱 Arahan-Arahan Utama Bot:
- `/start` : Menu alu-aluan dan panduan penggunaan.
- `/baca` : Memaparkan senarai 13 bab Al-Raqaiq untuk dibaca.
- `/mutiara` : Menjana mutiara kata hikmah rawak (Bahasa Arab bertasykil penuh + Terjemahan + Dimensi Haraki).
- `/cari <kata kunci>` : Mencari kata kunci di dalam teks terjemahan dan nota kaki.
- `/tazkirah` : Menjana tazkirah tazkiyah jiwa harian.
