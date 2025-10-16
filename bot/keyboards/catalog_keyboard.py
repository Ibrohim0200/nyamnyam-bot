from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.locale.get_lang import get_localized_text
from api.product_api import fetch_categories

def location_request_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_localized_text(lang, "catalog.location"), request_location=True)],
            [KeyboardButton(text=get_localized_text(lang, "menu.back"))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

async def catalog_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=get_localized_text(lang, "catalog.superbox"), callback_data="cat_surprise_bag")
    try:
        categories = await fetch_categories()
    except Exception:
        categories = []
    for cat in categories:
        kb.button(text=cat["title"], callback_data=f"cat_{cat['title']}")
    kb.button(text=get_localized_text(lang, "catalog.update_location"), callback_data="update_location")
    kb.button(text=get_localized_text(lang, "menu.back"), callback_data="back_to_menu")
    kb.adjust(2, 2, 1)
    return kb.as_markup()
