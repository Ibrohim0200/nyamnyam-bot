from bot.config.env import BASE_URL
from aiogram.utils.keyboard import InlineKeyboardBuilder


def start_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇿 O‘zbek", callback_data="lang_uz")
    kb.button(text="🇷🇺 Русский", callback_data="lang_ru")
    kb.button(text="🇬🇧 English", callback_data="lang_en")
    kb.adjust(2,1)
    return kb.as_markup()

def main_menu_keyboard(user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Catalog", callback_data="catalog")
    kb.button(text="🔑 Login", url=f"{BASE_URL}users/auth/login/?user_id={user_id}")
    kb.button(text="📝 Register", url=f"{BASE_URL}users/auth/register/?user_id={user_id}")
    kb.button(text="⚙️ Test", callback_data="test")
    kb.adjust(1)
    return kb.as_markup()
