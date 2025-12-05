from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from types import SimpleNamespace

from sqlalchemy import select

from api.user import get_valid_access_token
from bot.database.db_config import async_session_maker
from bot.database.models import UserTokens
from bot.database.views import get_user_lang
from bot.handlers.profile_handler import show_profile
from bot.handlers.register_handler import register_start, login_start
from bot.keyboards.start_keyboard import main_menu_keyboard
from bot.locale.get_lang import get_localized_text

router = Router()



class FakeCallback(SimpleNamespace):
    def __init__(self, message, bot):
        super().__init__(
            message=message,
            bot=bot,
            from_user=message.from_user,
            data=None
        )

    async def answer(self, *args, **kwargs):
        return

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



@router.message(Command("login"))
async def login_command(message: Message, state: FSMContext):
    fake = FakeCallback(message, message.bot)
    await login_start(fake, state)

@router.message(Command("register"))
async def register_command(message: Message, state: FSMContext):
    fake = FakeCallback(message, message.bot)
    await register_start(fake, state)

@router.message(Command("profile"))
async def profile_command(message: types.Message):
    fake = FakeCallback(message, message.bot)
    await show_profile(fake)



@router.callback_query(F.data == "help")
async def open_help(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)

    lang = (await state.get_data()).get("lang", "uz")
    text_template = get_localized_text(lang, "help.text")
    text = text_template.format(email="support@example.com")
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text= get_localized_text(lang, "menu.back"),
                callback_data="back_to_main_menu"
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
        lang = await get_user_lang(user_id)

    kb = await build_main_menu(user_id, lang)
    await callback.message.answer(get_localized_text(lang, "menu.main"), reply_markup=kb)



@router.message(Command("menu"))
async def menu_command(message: Message):
    user_id = message.from_user.id
    lang = await get_user_lang(user_id)
    async with async_session_maker() as db:
        result = await db.execute(
            select(UserTokens).where(UserTokens.telegram_id == user_id)
        )
        tokens = result.scalar_one_or_none()

    if not tokens or not tokens.access_token:
        await message.answer(
            get_localized_text(lang, "menu.main"),
            reply_markup=main_menu_keyboard(lang, user_id)
        )
        return

    menu = await build_main_menu(user_id, lang)
    await message.answer(get_localized_text(lang, "menu.main"), reply_markup=menu)
