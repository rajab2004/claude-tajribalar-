from aiogram.fsm.state import State, StatesGroup


class UserAuthStates(StatesGroup):
    waiting_password = State()           # Kirish uchun parol
    waiting_old_password = State()       # Parol o'zgartirish - eski parol
    waiting_new_password = State()       # Parol o'zgartirish - yangi parol
    waiting_confirm_password = State()   # Parol o'zgartirish - tasdiqlash


class PhoneAuthStates(StatesGroup):
    waiting_phone = State()       # Telefon raqam
    waiting_code = State()        # SMS/Telegram kodi
    waiting_2fa = State()         # 2FA paroli


class ChannelStates(StatesGroup):
    waiting_link = State()        # Yangi kanal linki


class AnnouncementStates(StatesGroup):
    waiting_text = State()        # E'lon matni
    confirm = State()             # Tasdiqlash


class SettingsStates(StatesGroup):
    waiting_old_password = State()
    waiting_new_password = State()
    waiting_confirm_password = State()
