from aiogram.fsm.state import StatesGroup, State

class UserState(StatesGroup):
    waiting_for_location = State()