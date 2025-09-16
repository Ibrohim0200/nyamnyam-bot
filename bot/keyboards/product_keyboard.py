from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.locale.get_lang import get_localized_text

ITEMS_PER_PAGE = 5

def products_pagination_keyboard(lang: str, category: str, page: int, total_pages: int):
    kb = InlineKeyboardBuilder()

    start_index = (page - 1) * ITEMS_PER_PAGE + 1
    end_index = min(start_index + ITEMS_PER_PAGE - 1, total_pages * ITEMS_PER_PAGE)

    for i in range(start_index, end_index + 1):
        kb.button(
            text=str(i),
            callback_data=f"product_{category}_{i}"
        )

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(
            text=get_localized_text(lang, "pagination.prev"),
            callback_data=f"page_{category}_{page-1}"
        ))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(
            text=get_localized_text(lang, "pagination.next"),
            callback_data=f"page_{category}_{page+1}"
        ))

    if nav_row:
        kb.row(*nav_row)

    kb.button(
        text=get_localized_text(lang, "menu.back"),
        callback_data=f"cat_{category}"
    )
    kb.adjust(5, 2, 1)
    return kb.as_markup()