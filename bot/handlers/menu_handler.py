from aiogram import Router, F, types
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locale.get_lang import get_localized_text
from bot.handlers.cart_handler import USER_CARTS, PRODUCTS

router = Router()


def get_cart_total(user_id: int) -> str:
    cart = USER_CARTS.get(user_id, {})
    total = 0
    for category, items in cart.items():
        for prod_id, qty in items.items():
            try:
                price = int(PRODUCTS[category][prod_id]["price"].replace(" ", "").replace("so‘m", ""))
                total += price * qty
            except Exception:
                continue
    return f"{total:,} so‘m"


def build_main_menu(lang: str, user_id: int):
    total = get_cart_total(user_id)

    kb = InlineKeyboardBuilder()
    kb.button(text=f"📦 {get_localized_text(lang, 'menu.catalog')}", callback_data="catalog")
    kb.button(text=f"🛒 {get_localized_text(lang, 'menu.cart')}", callback_data="cart")
    kb.button(text=f"👤 {get_localized_text(lang, 'menu.profile')}", callback_data="profile")
    kb.button(text=f"📜 {get_localized_text(lang, 'menu.orders')}", callback_data="orders")
    kb.button(text=f"❓ {get_localized_text(lang, 'menu.help')}", callback_data="help")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "test")
async def test_entry(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "uz")
    kb = build_main_menu(lang, callback.from_user.id)
    await callback.message.edit_text(get_localized_text(lang, "menu.main"), reply_markup=kb)


@router.callback_query(F.data == "catalog")
async def open_catalog(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "uz")
    await callback.answer()
    await callback.message.answer(get_localized_text(lang, "menu.catalog_clicked"))


@router.callback_query(F.data == "cart")
async def open_cart(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "uz")
    await callback.answer()
    await callback.message.answer(get_localized_text(lang, "menu.cart_clicked"))


@router.callback_query(F.data == "help")
async def open_help(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "uz")
    text_template = get_localized_text(lang, "help.text")
    text = text_template.format(email="support@example.com")
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text= get_localized_text(lang, "menu.back"),
                callback_data="back_profile"
            )]
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

