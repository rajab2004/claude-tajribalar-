import os
from dotenv import load_dotenv

load_dotenv()

# Bot
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Telegram API
API_ID: int = int(os.getenv("API_ID", "0"))
API_HASH: str = os.getenv("API_HASH", "")

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "")

# Admin
ADMIN_TELEGRAM_ID: int = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
ADMIN_GMAIL: str = os.getenv("ADMIN_GMAIL", "")
ADMIN_PHONE: str = os.getenv("ADMIN_PHONE", "")
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "")

# Gmail SMTP
GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")

# Encryption
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

# Cheklovlar
MAX_WRONG_ATTEMPTS: int = 10
MAX_CHANNELS: int = 150
DEFAULT_INTERVAL: int = 5
OTP_EXPIRE_SECONDS: int = 300
OTP_MAX_ATTEMPTS: int = 3
SESSION_SEND_DELAY: float = 0.8

# Timezone
TIMEZONE: str = "Asia/Tashkent"

def validate_config():
    required = {
        "BOT_TOKEN": BOT_TOKEN,
        "API_ID": API_ID,
        "API_HASH": API_HASH,
        "DATABASE_URL": DATABASE_URL,
        "ADMIN_TELEGRAM_ID": ADMIN_TELEGRAM_ID,
        "ADMIN_PASSWORD": ADMIN_PASSWORD,
        "ENCRYPTION_KEY": ENCRYPTION_KEY,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"❌ .env faylda yetishmayapti: {', '.join(missing)}")
    if len(ENCRYPTION_KEY) < 32:
        raise ValueError("❌ ENCRYPTION_KEY kamida 32 belgi bo'lishi kerak!")
