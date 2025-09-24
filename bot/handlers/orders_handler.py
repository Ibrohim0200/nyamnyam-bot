from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.db_config import async_session_maker
from bot.state.user_state import UserState
from bot.database.models import Order, UserLang
from bot.locale.get_lang import get_localized_text
from bot.keyboards.orders_keyboard import build_orders_keyboard
from math import radians, cos, sin, asin, sqrt

router = Router()

ORDERS_PER_PAGE = 5

@router.callback_query(F.data == "orders")
async def open_orders(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    telegram_id = callback.from_user.id


    result = await session.execute(select(UserLang).where(UserLang.telegram_id == telegram_id))
    user_lang = result.scalar_one_or_none()
    lang = user_lang.lang if user_lang else "uz"


    await state.update_data(page=0)


    result = await session.execute(
        select(Order).where(Order.telegram_id == telegram_id).order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    if not orders:
        await callback.message.edit_text(get_localized_text(lang, "orders.empty"))
    else:
        await show_orders(callback, orders, 0, lang)

    await state.set_state(UserState.buyurtma)
    await callback.answer()


@router.callback_query(F.data.startswith("orders_page:"))
async def paginate_orders(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    telegram_id = callback.from_user.id


    result = await session.execute(select(UserLang).where(UserLang.telegram_id == telegram_id))
    user_lang = result.scalar_one_or_none()
    lang = user_lang.lang if user_lang else "uz"


    result = await session.execute(
        select(Order).where(Order.telegram_id == telegram_id).order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    await show_orders(callback, orders, page, lang)
    await callback.answer()



async def show_orders(callback, orders, page: int, lang: str):
    total_orders = len(orders)
    total_pages = max((total_orders - 1) // ORDERS_PER_PAGE + 1, 1)
    page = max(0, min(page, total_pages - 1))

    start = page * ORDERS_PER_PAGE
    end = start + ORDERS_PER_PAGE
    orders_page = orders[start:end]

    if not orders_page:
        await callback.message.edit_text(get_localized_text(lang, "orders.empty"))
        return

    text = get_localized_text(lang, "orders.title") + "\n\n"
    for idx, order in enumerate(orders_page, start=1 + start):
        if order.status == "bekor qilingan":
            status_text = get_localized_text(lang, "order_status.cancelled")
        elif order.payment_status == "paid" and order.pickup_status == "pending":
            status_text = f"{get_localized_text(lang, 'order_status.paid')}, {get_localized_text(lang, 'order_status.pending')}"
        elif order.payment_status == "paid" and order.pickup_status == "picked_up":
            status_text = f"{get_localized_text(lang, 'order_status.paid')}, {get_localized_text(lang, 'order_status.picked_up')}"
        else:
            status_text = get_localized_text(lang, "order_status.unknown")
        text += (
            f"{idx}) {order.items[0]['product_name']} ×{order.items[0]['quantity']} — {int(order.total_price)} so‘m\n"
            f"   {get_localized_text(lang, 'orders.status')}: {status_text}\n"
            f"   {get_localized_text(lang, 'orders.pickup_time')}: {order.pickup_time}\n\n"
        )

    select_text = get_localized_text(lang, "orders.select_number")
    numbers = " ".join(str(i) for i in range(1 + start, 1 + start + len(orders_page)))
    text += f"{select_text}: {numbers}\n\n"

    keyboard = build_orders_keyboard(
        orders_page=orders_page,
        page=page,
        total_orders=total_orders,
        lang=lang
    )

    await callback.message.edit_text(text, reply_markup=keyboard)

def calculate_distance(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return round(km, 2)

@router.callback_query(F.data.startswith("order_detail:"))
@router.callback_query(F.data.startswith("order_detail:"))
async def order_detail_handler(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    order_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0
    telegram_id = callback.from_user.id

    async with async_session_maker() as session:
        result = await session.execute(select(UserLang).where(UserLang.telegram_id == telegram_id))
        user_lang = result.scalar_one_or_none()
        lang = user_lang.lang if user_lang else "uz"

        result = await session.execute(
            select(Order).where(Order.id == order_id, Order.telegram_id == telegram_id)
        )
        order = result.scalar_one_or_none()

    if not order:
        await callback.answer("❌ Order not found", show_alert=True)
        return


    if order.status == "bekor qilingan":
        text = (
            f"🧾 {get_localized_text(lang, 'orders.detail_title')}\n\n"
            f"{order.items[0]['product_name']} ×{order.items[0]['quantity']}\n"
            f"Narxi: {int(order.total_price)} {get_localized_text(lang, 'orders.currency')}\n"
            f"Holati: {get_localized_text(lang, 'order_status.cancelled')}"
        )
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text="↩️ " + get_localized_text(lang, "orders.back"),
                callback_data=f"orders_page:{page}"
            )]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        return

    if order.payment_status == "paid" and order.pickup_status == "pending":
        status_text = f"{get_localized_text(lang, 'order_status.paid')}, {get_localized_text(lang, 'order_status.pending')}"
    elif order.payment_status == "paid" and order.pickup_status == "picked_up":
        status_text = f"{get_localized_text(lang, 'order_status.paid')}, {get_localized_text(lang, 'order_status.picked_up')}"
    else:
        status_text = get_localized_text(lang, "order_status.unknown")

    text = f"{get_localized_text(lang, 'orders.detail_title')}\n\n"
    text += f"{get_localized_text(lang, 'orders.id')} {order.id}\n"
    text += f"{get_localized_text(lang, 'orders.total_price')} {int(order.total_price)} {get_localized_text(lang, 'orders.currency')}\n"
    text += f"{get_localized_text(lang, 'orders.status')}: {status_text}\n"
    text += f"{get_localized_text(lang, 'orders.branch')}: {order.branch_name}\n"
    text += f"{get_localized_text(lang, 'orders.items')}:\n"

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text="↩️ " + get_localized_text(lang, "orders.back"),
            callback_data=f"orders_page:{page}"
        )]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
