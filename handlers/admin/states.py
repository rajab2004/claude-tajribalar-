from aiogram.fsm.state import State, StatesGroup


class AdminAuthStates(StatesGroup):
    waiting_password = State()


class AdminSettingsStates(StatesGroup):
    waiting_new_password = State()
    waiting_confirm_password = State()
    waiting_new_gmail = State()
    waiting_new_phone = State()
    waiting_new_username = State()
    waiting_user_id_for_reset = State()


class AddUserStates(StatesGroup):
    waiting_telegram_id = State()
    waiting_phone = State()
    waiting_months = State()
    confirm = State()
