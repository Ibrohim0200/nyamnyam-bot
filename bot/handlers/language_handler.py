from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from bot.state.user_state import UserState
from bot.locale.get_lang import get_localized_text
from bot.keyboards.start_keyboard import main_menu_keyboard
from bot.database.db_config import async_session_maker
from bot.database.models import UserLang
from sqlalchemy import select

router = Router()

@router.callback_query(F.data.startswith("lang_"), StateFilter(UserState.choose_language))
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

        await session.commit()

    await state.clear()

    kb = await main_menu_keyboard(user_id)

    await callback.message.edit_text(
        get_localized_text(lang, "start.language_selected"),
        reply_markup=kb
    )
    await callback.answer()
