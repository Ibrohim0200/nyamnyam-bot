from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.locale.get_lang import get_localized_text

def location_request_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Joylashuvni ulashish", request_location=True)],
            [KeyboardButton(text="⬅️ Ortga")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def catalog_menu_keyboard(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=get_localized_text(lang, "catalog.all"), callback_data="cat_all")
    kb.button(text=get_localized_text(lang, "catalog.superbox"), callback_data="cat_superbox")
    kb.button(text=get_localized_text(lang, "catalog.food"), callback_data="cat_food")
    kb.button(text=get_localized_text(lang, "catalog.fastfood"), callback_data="cat_fastfood")
    kb.button(text=get_localized_text(lang, "catalog.update_location"), callback_data="update_location")
    kb.button(text=get_localized_text(lang, "menu.back"), callback_data="back_to_menu")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()