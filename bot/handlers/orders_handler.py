from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.user import fetch_orders_from_api, fetch_order_history
from bot.database.db_config import async_session_maker
from bot.database.models import UserTokens
from bot.keyboards.start_keyboard import main_menu_keyboard
from bot.locale.get_lang import get_localized_text
from bot.state.user_state import UserState
from bot.database.views import get_user_lang
from bot.keyboards.orders_keyboard import build_orders_keyboard

router = Router()

ORDERS_PER_PAGE = 5


# ===============================
# 📌 1) BUYURTMALAR OYNASI
# ===============================

@router.callback_query(F.data == "orders")
async def open_orders(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)
        result = await db.execute(
            select(UserTokens).where(UserTokens.telegram_id == user_id)
        )
        tokens = result.scalar_one_or_none()

    if not tokens or not tokens.access_token:
        await callback.message.answer(
            get_localized_text(lang, "profile.no_token"),
            reply_markup=main_menu_keyboard(lang, user_id)
        )
        return

    token = tokens.access_token
    await state.update_data(page=0)
    orders = await fetch_orders_from_api(token)
    if not orders:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_localized_text(lang, "menu.back"), callback_data="back_to_main_menu")]])
        await callback.message.edit_text(get_localized_text(lang, "orders.empty"), reply_markup=kb)
        return

    await show_orders(callback, orders, 0, lang)
    await state.set_state(UserState.buyurtma)
    # await callback.answer()


# ===============================
# 📌 2) PAGINATION
# ===============================

@router.callback_query(F.data.startswith("orders_page:"))
async def paginate_orders(callback: types.CallbackQuery, state: FSMContext):

    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    async with async_session_maker() as db:

        lang = await get_user_lang(user_id)

        result = await db.execute(
            select(UserTokens).where(UserTokens.telegram_id == user_id)
        )
        tokens = result.scalar_one_or_none()

    if not tokens or not tokens.access_token:
        await callback.answer(
            get_localized_text(lang, "profile.no_token"), show_alert=True
        )
        return

    token = tokens.access_token
    orders = await fetch_orders_from_api(token)

    try:
        await callback.message.delete()
    except:
        pass
    await show_orders(callback, orders, page, lang)
    await callback.answer()


# ===============================
# 📌 3) BUYURTMALAR RO‘YXATI
# ===============================

async def show_orders(callback, orders, page: int, lang: str):
    total_orders = len(orders)
    total_pages = max((total_orders - 1) // ORDERS_PER_PAGE + 1, 1)
    page = max(0, min(page, total_pages - 1))
    start = page * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    page_orders = orders[start:end]
    text = get_localized_text(lang, "orders.title") + "\n\n"

    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    for idx, order in enumerate(page_orders, start=start + 1):
        item = order["order_items"][0]

        status = item["status"]
        if status == "pending":
            status_text = get_localized_text(lang, "order_status.pending")
        elif status == "ready":
            status_text = get_localized_text(lang, "order_status.ready")
        elif status == "canceled":
            status_text = get_localized_text(lang, "order_status.cancelled")
        else:
            status_text = get_localized_text(lang, "order_status.unknown")

        text += (
            f"{idx}) {item['title']} ×{item['count']} — {order['total_price']} so‘m\n"
            f"   {get_localized_text(lang, 'orders.status')}: {status_text}\n"
            f"   {get_localized_text(lang, 'orders.pickup_date')}: {item['pickup_date']}\n"
            f"   {get_localized_text(lang, 'orders.branch')}: {item['business_branch_name']}\n\n"
        )

    numbers = " ".join(str(i) for i in range(start + 1, start + 1 + len(page_orders)))
    text += f"{get_localized_text(lang, 'orders.select_number')}: {numbers}\n\n"

    keyboard = build_orders_keyboard(
        orders_page=page_orders,
        page=page,
        total_orders=total_orders,
        lang=lang
    )

    await callback.message.answer(text=text, reply_markup=keyboard)


# ===============================
# 📌 4) BUYURTMA DETALI
# ===============================

@router.callback_query(F.data.startswith("order_detail:"))
async def order_detail_handler(callback: types.CallbackQuery, state: FSMContext):
    order_id = callback.data.split(":")[1]
    user_id = callback.from_user.id

    async with async_session_maker() as db:

        lang = await get_user_lang(user_id)

        result = await db.execute(
            select(UserTokens).where(UserTokens.telegram_id == user_id)
        )
        tokens = result.scalar_one_or_none()

    if not tokens or not tokens.access_token:
        await callback.answer(
            get_localized_text(lang, "profile.no_token"), show_alert=True
        )
        return

    token = tokens.access_token
    orders = await fetch_orders_from_api(token)
    order = next((o for o in orders if o["id"] == order_id), None)

    if not order:
        await callback.answer("❌ Order not found", show_alert=True)
        return

    item = order["order_items"][0]
    qr_url = item.get("qr_code_img")


    text = (
        f"🧾 <b>{get_localized_text(lang, 'orders.detail_title')}</b>\n\n"
        f"<b>{item['title']}</b> - {item['count']}\n"
        f"<b>{get_localized_text(lang, 'orders.total_price')}</b> - {order['total_price']} so‘m\n"
        f"<b>{get_localized_text(lang, 'orders.status')}</b> - {get_localized_text(lang, 'order_status.pending')}\n"
        f"<b>{get_localized_text(lang, 'orders.branch')}</b> - {item['business_branch_name']}\n"
        f"<b>{get_localized_text(lang, 'orders.pickup_date')}</b> - {item['pickup_date']}\n"
        f"<b>{get_localized_text(lang, 'orders.pickup_time')}</b> - {item['start_time']}-{item['end_time']}\n"
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="↩️ " + get_localized_text(lang, "orders.back"),
                callback_data="orders"
            )
        ]
    ])

    try:
        await callback.message.delete()
    except:
        pass

    if qr_url:
        await callback.bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=qr_url,
            caption=text,
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            parse_mode="HTML",
            reply_markup=kb
        )

    await callback.answer()



@router.callback_query(F.data == "orders_history")
async def orders_history(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    async with async_session_maker() as db:
        lang = await get_user_lang(user_id)
        result = await db.execute(
            select(UserTokens).where(UserTokens.telegram_id == user_id)
        )
        tokens = result.scalar_one_or_none()

    if not tokens or not tokens.access_token:
        await callback.message.answer(get_localized_text(lang, "profile.no_token"))
        return

    history = await fetch_order_history(tokens.access_token)

    if not history:
        await callback.message.edit_text(
            get_localized_text(lang, "orders.history_empty"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_localized_text(lang, "orders.back"),
                        callback_data="orders"
                    )
                ]
            ])
        )
        return

    text = f"📜 *{get_localized_text(lang, 'orders.history_title')}*\n\n"

    for order in history:
        item = order["order_items"][0]

        text += (
            f"• {item['title']} ×{item['count']} — {order['total_price']} so‘m\n"
            f"  {get_localized_text(lang, 'orders.date')}: {item['pickup_date']}\n"
            f"  {get_localized_text(lang, 'orders.branch')}: {item['business_branch_name']}\n"
            f"  {get_localized_text(lang, 'orders.status')}: {item['status']}\n\n"
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⬅️ " + get_localized_text(lang, "orders.back"),
                callback_data="orders"
            )
        ]
    ])

    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="Markdown"
    )

