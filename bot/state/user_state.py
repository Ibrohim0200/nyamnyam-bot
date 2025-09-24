from aiogram.fsm.state import StatesGroup, State

class UserState(StatesGroup):
    waiting_for_location = State()
    choose_language = State()
    editing_name = State()
    editing_phone = State()
    editing_email = State()
    editing_password = State()
    buyurtma = State()