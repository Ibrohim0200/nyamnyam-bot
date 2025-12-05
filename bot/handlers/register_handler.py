from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
import re

from sqlalchemy import select

from bot.database.db_config import async_session_maker
from bot.database.models import UserTokens
from bot.database.views import get_user_lang, save_user_tokens
from bot.keyboards.start_keyboard import main_menu_keyboard
from bot.locale.get_lang import get_localized_text
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from api.user import send_register_data, verify_otp, send_login_data, set_user_password, get_valid_access_token

router = Router()


class RegisterStates(StatesGroup):
    waiting_for_contact = State()
    waiting_for_otp = State()
    waiting_for_name = State()
    waiting_for_password = State()


class LoginStates(StatesGroup):
    waiting_for_contact = State()
    waiting_for_password = State()




async def safe_delete(bot, chat_id, msg_id):
    try:
        await bot.delete_message(chat_id, msg_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass

def phone_request_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text=get_localized_text(lang, "register.ask_phone"),
                request_contact=True
            )],
            [KeyboardButton(
                text=get_localized_text(lang, "menu.back")
            )],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def back_from_contact_state(message, state, state_name):
    user_id = message.from_user.id
    lang = await get_user_lang(user_id)
    back_text = get_localized_text(lang, "menu.back")
    if message.text == back_text:
        await state.clear()
        async with async_session_maker() as db:
            result = await db.execute(
                select(UserTokens).where(UserTokens.telegram_id == user_id)
            )
            tokens = result.scalar_one_or_none()
        if tokens and tokens.access_token:
            from bot.handlers.menu_handler import build_main_menu
            kb = await build_main_menu(user_id, lang)
        else:
            kb = main_menu_keyboard(lang, user_id)
        await message.answer(get_localized_text(lang, "menu.main"), reply_markup=kb)
        return True
    return False



@router.callback_query(F.data == "cancel")
async def cancel_any(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    user_id = callback.from_user.id
    lang = await get_user_lang(user_id)
    async with async_session_maker() as db:
        result = await db.execute(
            select(UserTokens).where(UserTokens.telegram_id == user_id)
        )
        tokens = result.scalar_one_or_none()

    if tokens and tokens.access_token:
        from bot.handlers.menu_handler import build_main_menu
        menu = await build_main_menu(user_id, lang)
        await callback.message.answer(
            get_localized_text(lang, "menu.main"),
            reply_markup=menu
        )
        return
    await callback.message.answer(
        get_localized_text(lang, "menu.main"),
        reply_markup=main_menu_keyboard(lang, user_id)
    )



def cancel_keyboard(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_localized_text(lang, "menu.back"),
                    callback_data="cancel"
                )
            ]
        ]
    )


@router.callback_query(F.data == "register")
async def register_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    bot = callback.bot
    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)
    await safe_delete(bot, chat_id, callback.message.message_id)
    reply_kb = phone_request_keyboard(lang)
    msg = await callback.message.answer(get_localized_text(lang, "register.ask_contact"), reply_markup=reply_kb)
    await state.set_state(RegisterStates.waiting_for_contact)
    await state.update_data(ask_msg_id=msg.message_id)
    await callback.answer()



@router.message(StateFilter(RegisterStates.waiting_for_contact))
async def register_receive_contact(message: types.Message, state: FSMContext):
    if await back_from_contact_state(message, state, "register_contact"):
        return
    user_id = message.from_user.id
    bot = message.bot
    chat_id = message.chat.id
    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
        contact_value = phone
        is_email = False
    else:
        text = (message.text or "").strip()
        email_regex = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        phone_regex = r"^\+?[0-9\s\-\(\)]{6,20}$"
        is_email = bool(re.match(email_regex, text))
        is_phone = bool(re.match(phone_regex, text))
        if not (is_email or is_phone):
            await message.answer(
                get_localized_text(lang, "register.invalid_format"),
                reply_markup=cancel_keyboard(lang)
            )
            return
        contact_value = text

    data = await state.get_data()
    if ask_msg_id := data.get("ask_msg_id"):
        await safe_delete(bot, chat_id, ask_msg_id)
    await safe_delete(bot, chat_id, message.message_id)
    sending_msg = await message.answer(get_localized_text(lang, "register.sending"))
    payload = (
        {"email": contact_value} if is_email
        else {"phone_number": contact_value}
    )
    payload["chat_id"] = user_id
    try:
        resp = await send_register_data(payload, is_email)
        await safe_delete(bot, chat_id, sending_msg.message_id)
        if resp.get("success") or resp.get("otp_sent"):
            msg = await message.answer(
                get_localized_text(lang, "register.enter_otp"),
                reply_markup=cancel_keyboard(lang)
            )
            await state.set_state(RegisterStates.waiting_for_otp)
            await state.update_data(
                ask_msg_id=msg.message_id,
                contact_value=contact_value,
                is_email=is_email
            )
        else:
            await message.answer(
                get_localized_text(lang, "register.server_error").format(
                    code=400, error=resp.get("message", "Unknown error")),
                reply_markup=cancel_keyboard(lang))
    except Exception as e:
        await message.answer(
            get_localized_text(lang, "register.exception").format(error=str(e)),
            reply_markup=cancel_keyboard(lang))
        await state.clear()





@router.message(StateFilter(RegisterStates.waiting_for_otp))
async def register_verify_otp(message: types.Message, state: FSMContext):
    bot = message.bot
    chat_id = message.chat.id
    user_id = message.from_user.id
    otp = (message.text or "").strip()
    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)

    data = await state.get_data()
    contact_value = data.get("contact_value")
    is_email = data.get("is_email", False)
    if ask_msg_id := data.get("ask_msg_id"):
        await safe_delete(bot, chat_id, ask_msg_id)
    await safe_delete(bot, chat_id, message.message_id)

    if not re.fullmatch(r"\d{4}", otp):
        await message.answer(get_localized_text(lang, "register.otp_invalid"),
                             reply_markup=cancel_keyboard(lang))
        return

    verifying_msg = await message.answer(get_localized_text(lang, "register.verifying"))

    payload = {"code": otp}
    payload["email" if is_email else "phone"] = contact_value

    resp = await verify_otp(payload)
    await safe_delete(bot, chat_id, verifying_msg.message_id)

    data_block = resp.get("data", {}).get("data") or resp.get("data")
    if not (resp.get("success") and data_block):
        err = resp.get("message") or resp.get("raw", {}).get("error_message") or "Invalid OTP"

        await message.answer(
            get_localized_text(lang, "register.verify_failed").format(error=err),
            reply_markup=cancel_keyboard(lang)
        )
        return

    server_user_id = data_block.get("id")
    await state.update_data(id=server_user_id)

    msg = await message.answer(
        get_localized_text(lang, "register.ask_first_name"),
        reply_markup=cancel_keyboard(lang)
    )
    await state.update_data(ask_msg_id=msg.message_id)
    await state.set_state(RegisterStates.waiting_for_name)




@router.message(StateFilter(RegisterStates.waiting_for_name))
async def register_receive_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    bot = message.bot
    chat_id = message.chat.id
    name = (message.text or "").strip()

    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)
    if not name:
        await message.answer(get_localized_text(lang, "register.name_empty"),
                             reply_markup=cancel_keyboard(lang))
        return
    parts = name.split()
    first_name = parts[0]
    last_name = " ".join(parts[1:]) if len(parts) > 1 else None
    data = await state.get_data()
    old_msg = data.get("ask_msg_id")
    if old_msg:
        await safe_delete(bot, chat_id, old_msg)

    await state.update_data(first_name=first_name, last_name=last_name)

    await safe_delete(bot, chat_id, message.message_id)
    msg = await message.answer(
        get_localized_text(lang, "register.ask_password"),
        reply_markup=cancel_keyboard(lang)
    )

    await state.update_data(ask_msg_id=msg.message_id)
    await state.set_state(RegisterStates.waiting_for_password)





@router.message(StateFilter(RegisterStates.waiting_for_password))
async def register_receive_password(message: types.Message, state: FSMContext):
    password = (message.text or "").strip()
    user_id = message.from_user.id
    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)
    if not password:
        await message.answer(get_localized_text(lang, "register.password_empty"),
                             reply_markup=cancel_keyboard(lang))
        return
    data = await state.get_data()
    server_id = data.get("id")
    first_name = data.get("first_name")
    if not server_id:
        await message.answer("❌ Server ID topilmadi. Ro‘yxatni qaytadan boshlang /register")
        await state.clear()
        return
    if not first_name:
        await message.answer(
            get_localized_text(lang, "register.password_empty"),
            reply_markup=cancel_keyboard(lang)
        )
        await state.set_state(RegisterStates.waiting_for_name)
        return

    resp = await set_user_password(server_id, password, first_name=first_name)
    if resp.get("success"):
        data_block = resp.get("raw", {}).get("data", {})
        tokens = data_block.get("tokens", {})
        access = tokens.get("access_token")
        refresh = tokens.get("refresh_token")
        if access and refresh:
            async with async_session_maker() as db:
                result = await db.execute(
                    select(UserTokens).where(UserTokens.telegram_id == user_id)
                )
                user_tokens = result.scalar_one_or_none()
                if user_tokens:
                    user_tokens.access_token = access
                    user_tokens.refresh_token = refresh
                else:
                    db.add(UserTokens(
                        telegram_id=user_id,
                        access_token=access,
                        refresh_token=refresh
                    ))

                await db.commit()
        await message.answer(get_localized_text(lang, "register.success")+"\n\n /menu")
    else:
        err = resp.get("message") or resp.get("raw", {}).get("error_message") or "Error"
        await message.answer(
            get_localized_text(lang, "register.password_failed").format(error=err),
            reply_markup=cancel_keyboard(lang)

        )
    await state.clear()






@router.callback_query(F.data == "login")
async def login_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    bot = callback.bot
    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)
    await safe_delete(bot, chat_id, callback.message.message_id)
    msg = await callback.message.answer(
        get_localized_text(lang, "login.ask_contact"),
        reply_markup=phone_request_keyboard(lang)
    )
    await state.set_state(LoginStates.waiting_for_contact)
    await state.update_data(ask_msg_id=msg.message_id)
    await callback.answer()


@router.message(StateFilter(LoginStates.waiting_for_contact))
async def login_receive_contact(message: types.Message, state: FSMContext):
    if await back_from_contact_state(message, state, "login_contact"):
        return
    user_id = message.from_user.id
    bot = message.bot
    chat_id = message.chat.id

    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
        contact_value = phone
        is_email = False
    else:
        text = (message.text or "").strip()
        email_regex = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        phone_regex = r"^\+?[0-9\s\-\(\)]{6,20}$"
        is_email = bool(re.match(email_regex, text))
        is_phone = bool(re.match(phone_regex, text))
        if not (is_email or is_phone):
            await message.answer(
                get_localized_text(lang, "register.invalid_format"),
                reply_markup=cancel_keyboard(lang)
            )
            return
        contact_value = text
    data = await state.get_data()
    if ask_msg_id := data.get("ask_msg_id"):
        await safe_delete(bot, chat_id, ask_msg_id)
    await safe_delete(bot, chat_id, message.message_id)
    msg = await message.answer(
        get_localized_text(lang, "login.ask_password"),
        reply_markup=cancel_keyboard(lang)
    )
    await state.set_state(LoginStates.waiting_for_password)
    await state.update_data(
        ask_msg_id=msg.message_id,
        contact_value=contact_value,
        is_email=is_email
    )



@router.message(StateFilter(LoginStates.waiting_for_password))
async def login_receive_password(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    bot = message.bot
    chat_id = message.chat.id
    password = (message.text or "").strip()

    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)

    data = await state.get_data()
    contact_value = data.get("contact_value")
    is_email = data.get("is_email", False)

    await safe_delete(bot, chat_id, message.message_id)
    if ask_msg_id := data.get("ask_msg_id"):
        await safe_delete(bot, chat_id, ask_msg_id)

    sending_msg = await message.answer(
        get_localized_text(lang, "login.sending"),
        reply_markup=cancel_keyboard(lang)
    )

    payload = {"password": password}
    payload["email" if is_email else "phone"] = contact_value

    try:
        resp = await send_login_data(payload)
        await safe_delete(bot, chat_id, sending_msg.message_id)

        tokens = resp.get("data", {}).get("tokens", {})
        access = tokens.get("access_token")
        refresh = tokens.get("refresh_token")

        if access and refresh:
            async with async_session_maker() as db:
                await save_user_tokens(db, user_id, access, refresh)
            await message.answer(get_localized_text(lang, "login.success"))
        else:
            await message.answer(
                get_localized_text(lang, "login.failed").format(
                    error=resp.get("message", "Invalid credentials")
                ),
                reply_markup=cancel_keyboard(lang)
            )

    except Exception as e:
        await safe_delete(bot, chat_id, sending_msg.message_id)
        await message.answer(
            get_localized_text(lang, "login.exception").format(error=str(e)),
            reply_markup=cancel_keyboard(lang)
        )

    await state.clear()

