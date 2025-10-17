import asyncio

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.db_config import async_session_maker
from bot.database.views import get_user_lang
from bot.locale.get_lang import get_localized_text

router = Router()


@router.callback_query(F.data == "checkout")
async def checkout_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    user_id = callback.from_user.id
    async with async_session_maker() as db:
        lang = await get_user_lang(db, user_id)
    cart = data.get("cart", [])

    if not cart:
        await callback.answer(get_localized_text(lang, "cart.empty"), show_alert=True)
        return

    text = f"{get_localized_text(lang, 'order.summary')}:\n"
    total = 0
    for item in cart:
        item_total = item["price"] * item["qty"]
        total += item_total
        text += f"🍔 {item['name']} ×{item['qty']} — {item_total:,} so‘m\n"
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
        lang = await get_user_lang(db, user_id)
    await state.update_data(cart=[])
    text = (
        f"{get_localized_text(lang, 'order.success')}\n\n"
        f"{get_localized_text(lang, 'order.payment_process')}\n"
        f" {get_localized_text(lang, 'order.payment_hint')}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_localized_text(lang, "order.payment_button"),
            url="https://payment-link.com/12345"
        )]
    ])
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(text, reply_markup=kb)

