# 🤖 Telegram Announcement Bot

Professional Telegram bot — foydalanuvchilar o'z Telegram akkauntlari orqali guruh va kanallarga avtomatik e'lon yuborishi uchun.

---

## 📋 Texnik Stack

| Texnologiya | Versiya | Maqsad |
|-------------|---------|--------|
| Python | 3.10+ | Dasturlash tili |
| Aiogram | 3.x | Telegram Bot framework |
| Pyrogram | 2.x | User account (xabar yuborish) |
| PostgreSQL | 14+ | Ma'lumotlar bazasi |
| SQLAlchemy | 2.x | Async ORM |
| APScheduler | 3.x | Background vazifalar |
| bcrypt | — | Parol xavfsizligi |
| AES-256-GCM | — | Sessiya shifrlash |

---

## 🗂 Fayl Strukturasi

```
bot/
├── main.py                    # Bot ishga tushirish
├── config.py                  # Konfiguratsiya
├── requirements.txt           # Kutubxonalar
├── .env.example               # Muhit o'zgaruvchilari namunasi
│
├── database/
│   ├── models.py              # 6 ta jadval (ORM modellari)
│   ├── crud.py                # Barcha DB operatsiyalari
│   └── connection.py          # Async engine va session
│
├── handlers/
│   ├── start.py               # /start komandasi
│   ├── user/
│   │   ├── auth.py            # Kirish, parol tekshiruvi
│   │   ├── channels.py        # Guruh/kanal boshqaruvi
│   │   ├── announcements.py   # E'lon yaratish va yuborish
│   │   ├── settings.py        # Sozlamalar, Pyrogram ulash
│   │   └── states.py          # FSM holatlari
│   └── admin/
│       ├── auth.py            # Admin kirish
│       ├── users.py           # Foydalanuvchi CRUD
│       ├── stats.py           # Statistika
│       ├── settings.py        # Admin sozlamalari
│       └── states.py          # FSM holatlari
│
├── middlewares/
│   ├── auth_middleware.py     # DB session, user/admin auth
│   └── rate_limit.py          # Spam himoya, logging
│
├── services/
│   ├── pyrogram_client.py     # Pyrogram ulash va xabar yuborish
│   ├── email_service.py       # Gmail SMTP
│   └── scheduler.py           # 4 ta background task
│
└── utils/
    ├── keyboards.py           # Barcha tugmalar (Reply + Inline)
    ├── helpers.py             # Yordamchi funksiyalar
    ├── password_generator.py  # Parol generatsiya, bcrypt
    └── encryption.py          # AES-256-GCM shifrlash
```

---

## 🗄 Ma'lumotlar Bazasi Jadvallari

```
admins       — Adminlar
users        — Foydalanuvchilar (muddatli kirish)
sessions     — Pyrogram sessiyalar (AES-256 shifrlangan)
channels     — Guruh/kanal linklar (max 150 ta)
announcements — E'lonlar (ochiq/yopiq)
send_logs    — Yuborish tarixi
```

---

## 🚪 Bot Menyusi

### 👤 Foydalanuvchi Paneli
| Bo'lim | Tavsif |
|--------|--------|
| 📱 Telegram akkauntni ulash | Pyrogram orqali akkount ulash (2FA qo'llab-quvvatlanadi) |
| 📢 Guruh va kanallar | Link qo'shish, ko'rish, o'chirish (max 150 ta) |
| 📝 Yangi e'lon yaratish | Xabar yozish va barcha guruhlarga yuborish |
| 📋 Mening e'lonlarim | Ochiq va yopilgan e'lonlar ro'yxati |
| 📞 Admin bilan bog'lanish | Admin telefon va username |
| ⚙️ Sozlamalar | Parol, interval, akkaunt uzish |

### 🔐 Admin Paneli
| Bo'lim | Tavsif |
|--------|--------|
| ➕ Foydalanuvchi qo'shish | Yangi foydalanuvchi + avtomatik parol + Telegram xabar |
| 👥 Foydalanuvchilar ro'yhati | Barchasi, faollar, muddati tugaganlar |
| 📊 Bot statistikasi | To'liq statistika |
| ⚙️ Admin sozlamalari | Parol, Gmail, bog'lanish ma'lumotlari |

---

## ⚙️ Fonga Ishlaydigan Vazifalar

| Vazifa | Jadval | Tavsif |
|--------|--------|--------|
| E'lon yuboruvchi | Har 1 daqiqada | Ochiq e'lonlarni intervalga qarab yuboradi |
| Muddat tekshiruvi | Har kecha 23:59 | Muddati tugagan userlarni deaktiv qiladi |
| E'lonlarni tozalash | Har kecha 00:00 | Yopilgan e'lonlarni o'chiradi |
| Sessiya tekshiruvi | Har 30 daqiqada | Uzilgan Pyrogram sessiyalarni aniqlaydi |

---

## 🔒 Xavfsizlik

- ✅ **Parollar** — bcrypt (rounds=12) bilan hash qilinadi
- ✅ **Sessiyalar** — AES-256-GCM bilan shifrlangan holda saqlanadi
- ✅ **Telegram ID + parol** juftligi tekshiriladi
- ✅ **10 marta noto'g'ri parol** — foydalanuvchi bloklanadi
- ✅ **Admin 10 marta noto'g'ri** — Gmail ga yangi parol yuboriladi
- ✅ **SQL injection** himoyasi — SQLAlchemy ORM
- ✅ **Rate limiting** — spam bosishlardan himoya
- ✅ **Barcha amallar** logga yoziladi
- ✅ **Maxfiy ma'lumotlar** faqat `.env` faylda (`.gitignore` da)

---

## 🚀 O'rnatish va Ishga Tushirish

### 1. Repozitoriyni klonlash
```bash
git clone https://github.com/rajab2004/claude-tajribalar-.git
cd claude-tajribalar-
```

### 2. Virtual muhit yaratish
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
# yoki
venv\Scripts\activate           # Windows
```

### 3. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. `.env` fayl yaratish
```bash
cp .env.example .env
```

### 5. `.env` faylni to'ldirish
```env
BOT_TOKEN=your_bot_token
BOT_USERNAME=your_bot_username
API_ID=your_pyrogram_api_id
API_HASH=your_pyrogram_api_hash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
ENCRYPTION_KEY=your_32_byte_base64_key
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
ADMIN_TELEGRAM_ID=your_telegram_id
ADMIN_USERNAME=your_username
ADMIN_PHONE=+998901234567
```

### 6. `ENCRYPTION_KEY` generatsiya qilish (bir marta)
```python
from utils.encryption import generate_encryption_key
print(generate_encryption_key())
# Natijani .env ga yozing
```

### 7. PostgreSQL bazani yaratish
```sql
CREATE DATABASE telegram_bot_db;
```

### 8. Botni ishga tushirish
```bash
python main.py
```

> ✅ Birinchi ishga tushishda jadvallar avtomatik yaratiladi va `ADMIN_TELEGRAM_ID` bilan admin qo'shiladi.
> 
> ⚠️ **Default admin paroli:** `Admin@2024!` — darhol o'zgartiring!

---

## 📦 Kerakli API kalitlar

| Kalit | Qayerdan olish |
|-------|----------------|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) |
| `API_ID` va `API_HASH` | [my.telegram.org](https://my.telegram.org) |
| `GMAIL_APP_PASSWORD` | [Google App Passwords](https://myaccount.google.com/apppasswords) |

---

## 📊 Bir Vaqtda Foydalanuvchilar

- **Optimal:** 50–100 ta
- **Maksimal:** 150 ta
- **Arxitektura:** To'liq asinxron (async/await)

---

## 📝 Litsenziya

MIT License — erkin foydalanishingiz mumkin.
