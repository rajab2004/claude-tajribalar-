import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Bot sozlamalari
    BOT_TOKEN: str
    BOT_USERNAME: str

    # Pyrogram
    API_ID: int
    API_HASH: str

    # Database
    DATABASE_URL: str

    # Xavfsizlik
    ENCRYPTION_KEY: str

    # Gmail
    GMAIL_USER: str
    GMAIL_APP_PASSWORD: str

    # Admin
    ADMIN_TELEGRAM_ID: int
    ADMIN_USERNAME: str
    ADMIN_PHONE: str


def load_config() -> Config:
    """Konfiguratsiyani .env fayldan yuklaydi"""

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN .env faylda topilmadi!")

    api_id = os.getenv("API_ID")
    if not api_id:
        raise ValueError("API_ID .env faylda topilmadi!")

    api_hash = os.getenv("API_HASH")
    if not api_hash:
        raise ValueError("API_HASH .env faylda topilmadi!")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL .env faylda topilmadi!")

    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY .env faylda topilmadi!")

    return Config(
        BOT_TOKEN=bot_token,
        BOT_USERNAME=os.getenv("BOT_USERNAME", ""),
        API_ID=int(api_id),
        API_HASH=api_hash,
        DATABASE_URL=database_url,
        ENCRYPTION_KEY=encryption_key,
        GMAIL_USER=os.getenv("GMAIL_USER", ""),
        GMAIL_APP_PASSWORD=os.getenv("GMAIL_APP_PASSWORD", ""),
        ADMIN_TELEGRAM_ID=int(os.getenv("ADMIN_TELEGRAM_ID", "0")),
        ADMIN_USERNAME=os.getenv("ADMIN_USERNAME", ""),
        ADMIN_PHONE=os.getenv("ADMIN_PHONE", ""),
    )


# Global config obyekti
config = load_config()
