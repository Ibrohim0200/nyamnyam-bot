import asyncio
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from bot.database.views import get_user_lang
from bot.state.user_state import UserState
from bot.keyboards.catalog_keyboard import location_request_keyboard, catalog_menu_keyboard
from bot.keyboards.start_keyboard import main_menu_keyboard
from bot.locale.get_lang import get_localized_text
from bot.database.db_config import async_session
from main import safe_delete

router = Router()

user_locations = {}

# ====================== Open Catalog ======================
@router.callback_query(F.data == "catalog")
async def catalog_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    bot = callback.bot

    async with async_session() as db:
        lang = await get_user_lang(db, user_id)
    await safe_delete(bot, chat_id, callback.message.message_id)

    if user_id not in user_locations:
        msg = await callback.message.answer(
            get_localized_text(lang, "catalog.send_location"),
            reply_markup=location_request_keyboard(lang)
        )
        await state.set_state(UserState.waiting_for_location)
        await asyncio.sleep(2)
        await msg.delete()
        return
    else:
        kb = await catalog_menu_keyboard(lang)
        await callback.message.answer(
            get_localized_text(lang, "catalog.choose_category"),
            reply_markup=kb
        )

    await callback.answer()




# ====================== Save Location ======================
@router.message(UserState.waiting_for_location, F.location)
async def save_location(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)
    user_locations[user_id] = (message.location.latitude, message.location.longitude)
    await state.clear()
    msg = await message.answer(
        get_localized_text(lang, "catalog.location_saved"),
        reply_markup=types.ReplyKeyboardRemove()
    )
    await asyncio.sleep(2)
    await msg.delete()

    await show_catalog_menu(message, lang)


# ====================== Back to Menu from Location ======================
@router.message(UserState.waiting_for_location)
async def back_to_menu_from_location(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)
        back_text = get_localized_text(lang, "menu.back")

    if message.text == back_text:
        await state.clear()
        await message.answer(
            get_localized_text(lang, "menu.title"),
            reply_markup=main_menu_keyboard(lang, user_id)
        )


# ====================== Show Catalog Menu ======================
async def show_catalog_menu(message: types.Message, lang: str):

    kb = await catalog_menu_keyboard(lang)
    await message.answer(
        get_localized_text(lang, "catalog.choose_category"),
        reply_markup=kb
    )


# ====================== Back to Main ======================
@router.callback_query(F.data == "back_to_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)

    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        get_localized_text(lang, "menu.main"),
        reply_markup=main_menu_keyboard(lang, user_id)
    )


# ====================== Update Location ======================
@router.callback_query(F.data == "update_location")
async def update_location(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)

    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        get_localized_text(lang, "catalog.update_location"),
        reply_markup=location_request_keyboard(lang)
    )
    await state.set_state(UserState.waiting_for_location)
