import httpx
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from bot.database.db_config import async_session_maker
from bot.database.models import UserTokens, UserLang
from bot.keyboards.start_keyboard import start_keyboard
from bot.locale.get_lang import get_localized_text
from api.user import get_user_profile, update_user_profile, refresh_access_token, get_tokens_by_user_id
from bot.handlers.register_handler import safe_delete
from bot.state.user_state import UserState

router = Router()


@router.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bot = callback.bot
    chat_id = callback.message.chat.id
    await safe_delete(bot, chat_id, callback.message.message_id)
    async with async_session_maker() as db:
        result_lang = await db.execute(
            select(UserLang).where(UserLang.telegram_id == user_id)
        )
        user_lang = result_lang.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"
        result = await db.execute(
            select(UserTokens).where(UserTokens.telegram_id == user_id)
        )
        tokens = result.scalar_one_or_none()
    if not tokens:
        await callback.message.answer(get_localized_text(lang, "profile.no_token"))
        return
    new_token_pack = await get_tokens_by_user_id(user_id)
    if new_token_pack.get("success") and new_token_pack.get("access"):
        access_token = new_token_pack["access"]
        refresh_token = new_token_pack["refresh"]
        async with async_session_maker() as session:
            user_tokens = await session.execute(
                select(UserTokens).where(UserTokens.telegram_id == user_id)
            )
            user_tokens = user_tokens.scalar_one_or_none()

            if user_tokens:
                user_tokens.access_token = access_token
                user_tokens.refresh_token = refresh_token
                await session.commit()
    try:
        profile_data = await get_user_profile(tokens.access_token)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            new_tokens = await refresh_access_token(user_id)
            if not new_tokens.get("success"):
                await callback.message.answer(
                    get_localized_text(lang, "profile.token_expired") + "\n\n/login"
                )
                return
            new_access = new_tokens.get("access_token")
            new_refresh = new_tokens.get("refresh_token")

            async with async_session_maker() as db:
                result = await db.execute(
                    select(UserTokens).where(UserTokens.telegram_id == user_id)
                )
                db_tokens = result.scalar_one_or_none()

                if db_tokens:
                    db_tokens.access_token = new_access
                    if new_refresh:
                        db_tokens.refresh_token = new_refresh
                    await db.commit()

            profile_data = await get_user_profile(new_access)

        else:
            await callback.message.answer(
                get_localized_text(lang, "profile.error").format(error=e.response.text)
            )
            return

    user = profile_data.get("data", {})

    first_name = user.get("first_name", "-")
    last_name = user.get("last_name", "-")
    birth_date = user.get("birth_date", "-")

    email = user.get("email")
    phone = user.get("phone_number")

    text = f"👤 <b>{get_localized_text(lang, 'profile.title')}</b>\n\n"
    text += f"👤 <b>{get_localized_text(lang, 'profile.first_name')}</b>: {first_name}\n"
    text += f"👤 <b>{get_localized_text(lang, 'profile.last_name')}</b>: {last_name}\n"
    text += f"🎂 <b>{get_localized_text(lang, 'profile.birth_date')}</b>: {birth_date}\n"

    if email:
        text += f"📧 <b>{get_localized_text(lang, 'profile.email')}</b>: {email}\n"
    if phone:
        text += f"📱 <b>{get_localized_text(lang, 'profile.phone')}</b>: {phone}\n"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_localized_text(lang, "profile.edit"),
                    callback_data="edit_profile",
                ),
                InlineKeyboardButton(
                    text=get_localized_text(lang, "profile.change_lang"),
                    callback_data="change_lang",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=get_localized_text(lang, "menu.back"),
                    callback_data="back_to_main_menu",
                )
            ],
        ]
    )

    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)



@router.callback_query(F.data == "change_lang")
async def change_lang_from_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserLang).where(UserLang.telegram_id == user_id)
        )
        user_lang = result.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        get_localized_text(lang, "start.choose_language"),
        reply_markup=start_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data == "edit_profile")
async def edit_profile_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    async with async_session_maker() as db:
        lang_obj = await db.execute(select(UserLang).where(UserLang.telegram_id == user_id))
        lang_row = lang_obj.scalar_one_or_none()
        lang = lang_row.lang if lang_row else "uz"

        token_obj = await db.execute(select(UserTokens).where(UserTokens.telegram_id == user_id))
        tokens = token_obj.scalar_one_or_none()

    profile = await get_user_profile(tokens.access_token)
    user = profile.get("data", {})

    kb = InlineKeyboardBuilder()

    kb.button(text=get_localized_text(lang, "profile.first_name"), callback_data="edit_first_name")
    kb.button(text=get_localized_text(lang, "profile.last_name"), callback_data="edit_last_name")
    kb.button(text=get_localized_text(lang, "profile.birth_date"), callback_data="edit_birth_date")
    kb.button(text=get_localized_text(lang, "profile_edit.password"), callback_data="edit_password")
    kb.button(text=get_localized_text(lang, "menu.back"), callback_data="profile")
    kb.adjust(2, 2, 2, 1)

    await callback.message.edit_text(
        get_localized_text(lang, "profile_edit.choose_field"),
        reply_markup=kb.as_markup()
    )
    await callback.answer()



@router.callback_query(F.data.startswith("edit_"))
async def edit_field_callback(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.replace("edit_", "")
    user_id = callback.from_user.id

    async with async_session_maker() as db:
        result = await db.execute(select(UserLang).where(UserLang.telegram_id == user_id))
        user_lang = result.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"

    await state.set_state(UserState.editing_field)
    await state.update_data(field=field)

    field_texts = {
        "first_name": "profile_edit.enter_first_name",
        "last_name": "profile_edit.enter_last_name",
        "email": "profile_edit.enter_email",
        "birth_date": "profile_edit.enter_birth_date",
        "phone": "profile_edit.enter_phone",
        "password": "profile_edit.enter_password",
    }

    await callback.message.edit_text(get_localized_text(lang, field_texts[field]))
    await callback.answer()


@router.message(UserState.editing_field)
async def save_edited_field(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    new_value = message.text
    data = await state.get_data()
    field = data.get("field")

    async with async_session_maker() as db:
        result = await db.execute(select(UserTokens).where(UserTokens.telegram_id == user_id))
        tokens = result.scalar_one_or_none()

        result2 = await db.execute(select(UserLang).where(UserLang.telegram_id == user_id))
        user_lang = result2.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"

    if not tokens:
        await message.answer(get_localized_text(lang, "profile.no_token"))
        return

    try:
        payload = {field: new_value}
        resp = await update_user_profile(tokens.access_token, payload)

        if resp.get("success"):
            kb = InlineKeyboardBuilder()
            kb.button(text=get_localized_text(lang, "menu.back"), callback_data="profile")
            await message.answer(get_localized_text(lang, "profile_edit.updated_field"), reply_markup=kb.as_markup())
        else:
            await message.answer(get_localized_text(lang, "profile.error").format(error=resp))
    except httpx.HTTPStatusError as e:
        await message.answer(get_localized_text(lang, "profile.error").format(error=e.response.text))

    await state.clear()