import asyncio

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from api.user import post_order, get_valid_access_token, refresh_access_token, get_tokens_by_user_id
from bot.database.db_config import async_session_maker
from bot.database.models import UserTokens
from bot.database.views import get_user_lang
from bot.keyboards.start_keyboard import main_menu_keyboard
from bot.locale.get_lang import get_localized_text

router = Router()


@router.callback_query(F.data == "checkout")
async def checkout_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    user_id = callback.from_user.id
    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)
        result = await db.execute(
            select(UserTokens).where(UserTokens.telegram_id == user_id)
        )
        tokens = result.scalar_one_or_none()

    if not tokens:
        await callback.message.answer(
            get_localized_text(lang, "profile.no_token"),
            reply_markup=main_menu_keyboard(lang, user_id)
        )
        return

    cart = data.get("cart", [])

    if not cart:
        await callback.answer(get_localized_text(lang, "cart.empty"), show_alert=True)
        return

    text = f"{get_localized_text(lang, 'order.summary')}:\n"
    total = 0
    for item in cart:
        item_total = item["price"] * item["count"]
        total += item_total
        text += f"🍔 {item['title']} ×{item['count']} — {item_total:,} so‘m\n"
    text += f"—\n{get_localized_text(lang, 'cart.grand_total')}: {total:,} so‘m"

    kb = InlineKeyboardBuilder()
    kb.button(text=get_localized_text(lang, "order.confirm"), callback_data="order_confirm")
    kb.button(text=get_localized_text(lang, "menu.back"), callback_data="cart")
    kb.adjust(2)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data == "order_confirm")
async def order_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)

    text = (
        f"{get_localized_text(lang, 'order.success')}\n\n"
        f"{get_localized_text(lang, 'order.payment_process')}\n"
        f"{get_localized_text(lang, 'order.payment_hint')}"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text=get_localized_text(lang, "order.payment_payme"), callback_data="order_pay_payme")
    kb.button(text=get_localized_text(lang, "order.payment_click"), callback_data="order_pay_click")
    kb.adjust(2)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(text, reply_markup=kb.as_markup())


async def send_long_message(message, text, parse_mode=None):
    MAX_LEN = 4000
    for i in range(0, len(text), MAX_LEN):
        await message.answer(text[i:i+MAX_LEN], parse_mode=parse_mode)





@router.callback_query(F.data.in_(["order_pay_payme", "order_pay_click"]))
async def process_payment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    user_id = callback.from_user.id

    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)

    data = await state.get_data()
    cart = data.get("cart", [])

    if not cart:
        return

    payment_method = "payme" if callback.data == "order_pay_payme" else "click"

    order_items = [
        {
            "title": item["title"],
            "count": item["count"],
            "price": item["price"],
            "surprise_bag": item["id"],
            "start_time": item.get("start_time", "string"),
            "end_time": item.get("end_time", "string"),
            "weekday": item.get("weekday", 0),
        }
        for item in cart
    ]

    async with async_session_maker() as session:
        user_tokens = await session.execute(
            select(UserTokens).where(UserTokens.telegram_id == user_id)
        )
        tokens = user_tokens.scalars().first()

    access_token = tokens.access_token
    try_new = await get_tokens_by_user_id(user_id)

    if try_new.get("success") and try_new.get("access"):
        access_token = try_new["access"]
        refresh_token = try_new["refresh"]
        async with async_session_maker() as session:
            db_tokens = await session.execute(
                select(UserTokens).where(UserTokens.telegram_id == user_id)
            )
            db_tokens = db_tokens.scalars().first()
            if db_tokens:
                db_tokens.access_token = access_token
                db_tokens.refresh_token = refresh_token
                await session.commit()
    response = await post_order(access_token, order_items, payment_method)
    if isinstance(response, dict) and response.get("status") == 401:
        refreshed = await refresh_access_token(user_id)
        if not refreshed.get("success"):
            await callback.message.answer(get_localized_text(lang, "token_expired"), "\n\n/login")
            return
        new_access = refreshed["access_token"]
        async with async_session_maker() as session:
            db_tokens = await session.execute(
                select(UserTokens).where(UserTokens.telegram_id == user_id)
            )
            db_tokens = db_tokens.scalars().first()
            if db_tokens:
                db_tokens.access_token = new_access
                await session.commit()
        response = await post_order(new_access, order_items, payment_method)

    if isinstance(response, dict) and response.get("success"):
        await state.update_data(cart=[])

        payment_url = (
            response.get("data", {}).get("payment_url")
            or response.get("payment_url")
        )

        kb = InlineKeyboardBuilder()
        kb.button(text=get_localized_text(lang, "order.pay"), url=payment_url)
        kb.adjust(1)

        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer("👇", reply_markup=kb.as_markup())

    else:
        error_text = response.get("error") if isinstance(response, dict) else str(response)

        try:
            import json
            err = json.loads(error_text)
            error_text = err.get("error_message", str(err))
        except Exception:
            pass

        full_error = f"{get_localized_text(lang, 'order.error')}\n\n{error_text}"

        await callback.message.answer(full_error)
