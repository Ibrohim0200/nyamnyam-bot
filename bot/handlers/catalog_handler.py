from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from bot.state.user_state import UserState
from bot.keyboards.catalog_keyboard import location_request_keyboard, catalog_menu_keyboard
from bot.keyboards.product_keyboard import products_pagination_keyboard
from bot.keyboards.start_keyboard import main_menu_keyboard
from bot.locale.get_lang import get_localized_text

router = Router()

user_locations = {}

@router.callback_query(F.data == "catalog")
async def catalog_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    user_id = callback.from_user.id
    if user_id not in user_locations:
        await callback.message.answer(
            get_localized_text(lang, "catalog.send_location"),
            reply_markup=location_request_keyboard()
        )
        await state.set_state(UserState.waiting_for_location)
    else:
        await show_catalog_menu(callback.message, lang)


@router.message(UserState.waiting_for_location, F.location)
async def save_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    user_locations[message.from_user.id] = (message.location.latitude, message.location.longitude)
    await state.clear()

    await message.answer(
        get_localized_text(lang, "catalog.location_saved"),
        reply_markup=types.ReplyKeyboardRemove()
    )
    await show_catalog_menu(message, lang)


@router.message(UserState.waiting_for_location, F.text == "⬅️ Ortga")
async def back_to_menu_from_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")

    await state.clear()

    await message.answer(
        get_localized_text(lang, "menu.main"),
        reply_markup=main_menu_keyboard()
    )


async def show_catalog_menu(message: types.Message, lang: str):

    await message.answer(
        get_localized_text(lang, "catalog.choose_category"),
        reply_markup=catalog_menu_keyboard(lang)
    )

