from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.keyboards.start_keyboard import start_keyboard, main_menu_keyboard
from bot.locale.get_lang import get_localized_text
from sqlalchemy import select
from bot.database.db_config import async_session_maker
from bot.database.models import UserLang

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        get_localized_text('uz', 'start.choose_language'),  # default uz
        reply_markup=start_keyboard()
    )


@router.callback_query(F.data.startswith("lang_"))
async def choose_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)

    user_id = callback.from_user.id

    async with async_session_maker() as session:
        result = await session.execute(
            select(UserLang).where(UserLang.telegram_id == callback.from_user.id)
        )
        user_lang = result.scalars().first()

        if user_lang:
            user_lang.lang = lang
        else:
            user_lang = UserLang(
                telegram_id=callback.from_user.id,
                lang=lang
            )
            session.add(user_lang)

        await session.commit()

    await callback.message.edit_text(
        get_localized_text(lang, "start.language_selected"),
        reply_markup=main_menu_keyboard(user_id)
    )


# @router.callback_query(F.data == "catalog")
async def catalog_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await callback.answer()
    await callback.message.answer(get_localized_text(lang, "menu.catalog_clicked"))

@router.callback_query(F.data == "login")
async def login_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await callback.answer()
    await callback.message.answer(get_localized_text(lang, "menu.login_clicked"))

@router.callback_query(F.data == "register")
async def register_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await callback.answer()
    await callback.message.answer(get_localized_text(lang, "menu.register_clicked"))



