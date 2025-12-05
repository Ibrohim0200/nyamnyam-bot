from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.locale.get_lang import get_localized_text

ORDERS_PER_PAGE = 5

def build_orders_keyboard(orders_page, page: int, total_orders: int, lang: str) -> InlineKeyboardMarkup:
    keyboard = []
    start_idx = page * ORDERS_PER_PAGE
    order_buttons = [
        InlineKeyboardButton(
            text=str(start_idx + idx + 1),
            callback_data=f"order_detail:{order['id']}"
        )
        for idx, order in enumerate(orders_page)
    ]
    if order_buttons:
        keyboard.append(order_buttons)

    total_pages = max((total_orders - 1) // ORDERS_PER_PAGE + 1, 1)
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ " + get_localized_text(lang, "orders.back"),
            callback_data=f"orders_page:{page - 1}"
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text=get_localized_text(lang, "orders.next") + " ➡️",
            callback_data=f"orders_page:{page + 1}"
        ))
    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append([
        InlineKeyboardButton(
            text="📜 " + get_localized_text(lang, "orders.history_title"),
            callback_data="orders_history"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            text=get_localized_text(lang, "menu.back"),
            callback_data="back_to_main_menu"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)




def build_order_detail_keyboard(page: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 " + get_localized_text(lang, "orders.back"),
                    callback_data=f"orders_page:{page}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 " + get_localized_text(lang, "orders.menu"),
                    callback_data="main_menu"
                )
            ]
        ]
    )
