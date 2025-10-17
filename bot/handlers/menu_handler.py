from aiogram import Router, F, types
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.db_config import async_session_maker
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
    async with async_session_maker() as db:
        lang = await get_user_lang(db, user_id)

    kb = await build_main_menu(user_id, lang)
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
    user_id = callback.from_user.id
    async with async_session_maker() as db:
        lang = await get_user_lang(db, user_id)

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



@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    user_id = callback.from_user.id
    async with async_session_maker() as db:
        lang = await get_user_lang(db, user_id)

    kb = await build_main_menu(user_id, lang)
    await callback.message.answer(get_localized_text(lang, "menu.main"), reply_markup=kb)
