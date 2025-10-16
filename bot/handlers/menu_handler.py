from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.db_config import async_session
from bot.database.views import get_user_lang
from bot.locale.get_lang import get_localized_text

router = Router()


async def get_cart_total(state: FSMContext) -> str:
    data = await state.get_data()
    cart = data.get("cart", [])
    total = 0
    for item in cart:
        total += item["price"] * item["qty"]
    return f"{total:,} so‘m"


async def build_main_menu(user_id: int, lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=f"{get_localized_text(lang, 'menu.catalog')}", callback_data="catalog")
    kb.button(text=f"🛒 {get_localized_text(lang, 'menu.cart')}", callback_data="cart")
    kb.button(text=f"👤 {get_localized_text(lang, 'menu.profile')}", callback_data="profile")
    kb.button(text=f"📜 {get_localized_text(lang, 'menu.orders')}", callback_data="orders")
    kb.button(text=f"❓ {get_localized_text(lang, 'menu.help')}", callback_data="help")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "test")
async def test_entry(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)

    kb = await build_main_menu(user_id, lang)
    await callback.message.edit_text(get_localized_text(lang, "menu.main"), reply_markup=kb)


@router.callback_query(F.data == "profile")
async def open_profile(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)

    await callback.answer()
    await callback.message.answer(get_localized_text(lang, "menu.profile_clicked"))


@router.callback_query(F.data == "orders")
async def open_orders(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)

    await callback.answer()
    await callback.message.answer(get_localized_text(lang, "menu.orders_clicked"))


@router.callback_query(F.data == "help")
async def open_help(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)

    await callback.answer()
    await callback.message.answer(get_localized_text(lang, "menu.help_clicked"))


@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)

    kb = await build_main_menu(user_id, lang)
    await callback.message.answer(get_localized_text(lang, "menu.main"), reply_markup=kb)
