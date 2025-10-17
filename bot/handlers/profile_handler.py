from datetime import datetime

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.crud.user import get_user
from bot.database.db_config import async_session_maker
from bot.database.models import UserLang, User
from bot.handlers.menu_handler import build_main_menu
from bot.keyboards.profile_keyboard import get_profile_keyboard, get_profile_edit_keyboard
from bot.state.user_state import UserState
from bot.keyboards.catalog_keyboard import location_request_keyboard, catalog_menu_keyboard
from bot.keyboards.product_keyboard import products_pagination_keyboard
from bot.keyboards.start_keyboard import main_menu_keyboard, start_keyboard
from bot.locale.get_lang import get_localized_text
from sqlalchemy import select
import re

PHONE_REGEX = re.compile(r"^\+998\d{9}$")
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$")



router = Router()

@router.callback_query(F.data == "profile")
async def profile_handler(callback: types.CallbackQuery, session: AsyncSession):
    telegram_id = callback.from_user.id

    result = await session.execute(
        select(UserLang).where(UserLang.telegram_id == telegram_id)
    )
    user_lang = result.scalar_one_or_none()
    lang = user_lang.lang if user_lang else "uz"

    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await callback.message.edit_text(
            text=get_localized_text(lang, "profile.not_found"),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_localized_text(lang,"profile_buttons.back"),
                        callback_data="back_profile"
                    )]
                ]
            )
        )
        return
    text = (
        f"{get_localized_text(lang, 'profile.title')}\n"
        f"{get_localized_text(lang, 'profile.name').format(name=user.full_name)}\n"
        f"{get_localized_text(lang, 'profile.contact').format(contact=user.phone)}\n"
        f"{get_localized_text(lang, 'profile.email').format(email=user.email)}\n"
        f"{get_localized_text(lang, 'profile.date').format(date=user.formatted_registered_at)}"
    )

    await callback.message.edit_text(text=text, reply_markup=get_profile_keyboard(lang))

@router.callback_query(F.data == "back_profile")
async def back_handler(callback: types.CallbackQuery, session: AsyncSession):
    telegram_id = callback.from_user.id

    result = await session.execute(
        select(UserLang).where(UserLang.telegram_id == telegram_id)
    )
    user_lang = result.scalar_one_or_none()
    lang = user_lang.lang if user_lang else "uz"
    kb = build_main_menu(lang, telegram_id)
    await callback.message.edit_text(
        text=get_localized_text(lang, "menu.title"),
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data == "change_lang")
async def change_lang_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.choose_language)

    lang = 'uz'
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserLang).where(UserLang.telegram_id == callback.from_user.id)
        )
        user_lang = result.scalars().first()
        if user_lang:
            lang = user_lang.lang

    await callback.message.edit_text(
        get_localized_text(lang, 'start.choose_language'),
        reply_markup=start_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "edit_profile")
async def edit_profile_handler(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id

    async with async_session_maker() as session:
        result = await session.execute(
            select(UserLang).where(UserLang.telegram_id == telegram_id)
        )
        user_lang = result.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"

    await callback.message.edit_text(
        text=get_localized_text(lang, "profile_edit.choose_field"),
        reply_markup=get_profile_edit_keyboard(lang)
    )
    await callback.answer()

@router.callback_query(F.data == "edit_name")
async def edit_name_callback(callback: types.CallbackQuery, state: FSMContext):
    async with async_session_maker() as session:
        result = await session.execute(select(UserLang).where(UserLang.telegram_id == callback.from_user.id))
        user_lang = result.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"

    await state.set_state(UserState.editing_name)
    await callback.message.edit_text(
        text=get_localized_text(lang, "profile_edit.enter_name")
    )
    await callback.answer()

@router.message(UserState.editing_name)
async def save_name(message: types.Message, state: FSMContext):
    new_name = message.text
    user_id = message.from_user.id

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.full_name = new_name
            await session.commit()

    await state.clear()

    async with async_session_maker() as session:
        result = await session.execute(select(UserLang).where(UserLang.telegram_id == user_id))
        user_lang = result.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"

    await message.answer(
        get_localized_text(lang, "profile_edit.updated_name"),
        reply_markup=get_profile_edit_keyboard(lang)
    )

@router.callback_query(F.data == "back_profile_show")
async def back_from_edit_profile(callback: types.CallbackQuery, session: AsyncSession):
    telegram_id = callback.from_user.id

    result = await session.execute(
        select(UserLang).where(UserLang.telegram_id == telegram_id)
    )
    user_lang = result.scalar_one_or_none()
    lang = user_lang.lang if user_lang else "uz"

    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await callback.message.edit_text(
            get_localized_text(lang, "profile.not_found"),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_localized_text(lang,"profile_buttons.back"),
                        callback_data="back_profile"
                    )]
                ]
            )
        )
        return

    text = (
        f"{get_localized_text(lang, 'profile.title')}\n"
        f"{get_localized_text(lang, 'profile.name').format(name=user.full_name)}\n"
        f"{get_localized_text(lang, 'profile.contact').format(contact=user.phone)}\n"
        f"{get_localized_text(lang, 'profile.email').format(email=user.email)}\n"
        f"{get_localized_text(lang, 'profile.date').format(date=user.formatted_registered_at)}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_profile_keyboard(lang)
    )
    await callback.answer()


@router.callback_query(F.data == "edit_phone")
async def edit_phone_callback(callback: types.CallbackQuery, state: FSMContext):
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserLang).where(UserLang.telegram_id == callback.from_user.id)
        )
        user_lang = result.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"

    await state.set_state(UserState.editing_phone)
    await callback.message.edit_text(
        text=get_localized_text(lang, "profile_edit.enter_phone")
    )
    await callback.answer()


@router.message(UserState.editing_phone)
async def save_phone(message: types.Message, state: FSMContext):
    new_phone = message.text
    user_id = message.from_user.id

    if not PHONE_REGEX.match(new_phone):
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserLang).where(UserLang.telegram_id == user_id)
            )
            user_lang = result.scalar_one_or_none()
            lang = user_lang.lang if user_lang else "uz"

        await message.answer(
            get_localized_text(lang, "profile_edit.invalid_phone")
        )
        return


    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.phone = new_phone
            await session.commit()

    await state.clear()

    async with async_session_maker() as session:
        result = await session.execute(
            select(UserLang).where(UserLang.telegram_id == user_id)
        )
        user_lang = result.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"

    await message.answer(
        get_localized_text(lang, "profile_edit.updated_phone"),
        reply_markup=get_profile_edit_keyboard(lang)
    )


@router.callback_query(F.data == "edit_email")
async def edit_email_callback(callback: types.CallbackQuery, state: FSMContext):
    async with async_session_maker() as session:
        result = await session.execute(select(UserLang).where(UserLang.telegram_id == callback.from_user.id))
        user_lang = result.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"

    await state.set_state(UserState.editing_email)
    await callback.message.edit_text(
        text=get_localized_text(lang, "profile_edit.enter_email")
    )
    await callback.answer()


@router.message(UserState.editing_email)
async def save_email(message: types.Message, state: FSMContext):
    new_email = message.text
    user_id = message.from_user.id

    if not EMAIL_REGEX.match(new_email):
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserLang).where(UserLang.telegram_id == user_id)
            )
            user_lang = result.scalar_one_or_none()
            lang = user_lang.lang if user_lang else "uz"

        await message.answer(
            get_localized_text(lang, "profile_edit.invalid_email")
        )
        return

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.email = new_email
            await session.commit()

    await state.clear()

    async with async_session_maker() as session:
        result = await session.execute(
            select(UserLang).where(UserLang.telegram_id == user_id)
        )
        user_lang = result.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"

    await message.answer(
        get_localized_text(lang, "profile_edit.updated_email"),
        reply_markup=get_profile_edit_keyboard(lang)
    )




