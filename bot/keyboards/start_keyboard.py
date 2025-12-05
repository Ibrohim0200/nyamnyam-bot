from bot.config.env import BASE_URL
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.locale.get_lang import get_localized_text


def start_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇿 O‘zbek", callback_data="lang_uz")
    kb.button(text="🇷🇺 Русский", callback_data="lang_ru")
    kb.button(text="🇬🇧 English", callback_data="lang_en")
    kb.adjust(2,1)
    return kb.as_markup()

def main_menu_keyboard(lang: str, user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text=get_localized_text(lang, "menu.catalog"), callback_data="catalog")
    kb.button(text=get_localized_text(lang, "menu.login_clicked"), callback_data="login")
    kb.button(text=get_localized_text(lang, "menu.register_clicked"), callback_data="register")
    kb.adjust(1)
    return kb.as_markup()
