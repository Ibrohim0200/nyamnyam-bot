from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from bot.database.views import get_user_lang
from bot.handlers.cart_handler import view_cart
from bot.keyboards.catalog_keyboard import location_request_keyboard
from bot.keyboards.start_keyboard import start_keyboard, main_menu_keyboard
from bot.handlers.catalog_handler import show_catalog_menu, user_locations
from bot.locale.get_lang import get_localized_text
from sqlalchemy import select
from bot.database.db_config import async_session_maker
from bot.database.models import UserLang
from bot.state.user_state import UserState

router = Router()


# =================== COMMANDS ===================
@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        get_localized_text('uz', 'start.choose_language'),
        reply_markup=start_keyboard()
    )



@router.message(Command("catalog"))
async def cmd_catalog(message: types.Message, state: FSMContext):
    class FakeCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
        async def answer(self, *args, **kwargs):
            pass

    fake_callback = FakeCallback(message)
    await catalog_handler(fake_callback, state)



@router.message(Command("cart"))
async def cmd_cart(message: types.Message, state: FSMContext):
    class FakeCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
        async def answer(self, *args, **kwargs):
            pass

    fake_callback = FakeCallback(message)
    await view_cart(fake_callback, state)




# LANGUAGE CALLBACK
@router.callback_query(F.data.startswith("lang_"))
async def choose_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)
    user_id = callback.from_user.id

    async with async_session_maker() as session:
        result = await session.execute(
            select(UserLang).where(UserLang.telegram_id == user_id)
        )
        user_lang = result.scalars().first()

        if user_lang:
            user_lang.lang = lang
        else:
            user_lang = UserLang(telegram_id=user_id, lang=lang)
            session.add(user_lang)

        await session.commit()  # ✅ сначала сохраняем
        await session.flush()

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        get_localized_text(lang, "start.language_selected"),
        reply_markup=main_menu_keyboard(lang, user_id)
    )
    await callback.answer()
    result2 = await session.execute(select(UserLang).where(UserLang.telegram_id == user_id))
    saved = result2.scalars().first()
    print("✅ SAVED LANG:", saved.lang if saved else None)

# MENU CALLBACKS
@router.callback_query(F.data == "catalog")
async def catalog_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    async with async_session_maker() as session:
        result = await session.execute(
            select(UserLang).where(UserLang.telegram_id == user_id)
        )
        user_lang = result.scalars().first()
        lang = user_lang.lang if user_lang else "uz"

    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    if user_id not in user_locations:
        await callback.message.answer(
            get_localized_text(lang, "catalog.send_location"),
            reply_markup=location_request_keyboard(lang)   # bu ReplyKeyboardMarkup
        )
        await state.set_state(UserState.waiting_for_location)
        return
    await show_catalog_menu(callback.message, lang)

@router.callback_query(F.data == "login")
async def login_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserLang).where(UserLang.telegram_id == user_id)
        )
        user_lang = result.scalars().first()
        lang = user_lang.lang if user_lang else "uz"

    await callback.answer()
    await callback.message.answer(get_localized_text(lang, "menu.login_clicked"))


@router.callback_query(F.data == "register")
async def register_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserLang).where(UserLang.telegram_id == user_id)
        )
        user_lang = result.scalars().first()
        lang = user_lang.lang if user_lang else "uz"

    await callback.answer()
    await callback.message.answer(get_localized_text(lang, "menu.register_clicked"))
