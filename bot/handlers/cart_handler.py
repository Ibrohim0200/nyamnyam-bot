from urllib.parse import quote

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.catalog_keyboard import catalog_menu_keyboard
from bot.keyboards.start_keyboard import main_menu_keyboard
from bot.locale.get_lang import get_localized_text
from bot.handlers.product_handler import extract_category_and_id
from bot.database.views import get_user_lang
from bot.database.db_config import async_session

router = Router()
user_carts = {}


async def show_catalog_menu(message: types.Message, lang: str):
    await message.answer(
        get_localized_text(lang, "catalog.choose_category"),
        reply_markup=catalog_menu_keyboard(lang)
    )


# ====================== Add to cart ======================
@router.callback_query(F.data.startswith("cart_add_"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    category, prod_id = extract_category_and_id(callback.data, 2)
    async with async_session() as db:
        lang = await get_user_lang(db, callback.from_user.id)

    data = await state.get_data()
    key = "superbox_items" if category == "superbox" else f"{category.lower()}_items"
    items = data.get(key, [])

    if not items or prod_id < 1 or prod_id > len(items):
        await callback.answer(get_localized_text(lang, "product.not_found"), show_alert=True)
        return

    product = items[prod_id - 1]
    qty_data = data.get("qty_temp", {})
    key_qty = f"{category}_{prod_id}"
    qty = qty_data.get(key_qty, 1)

    cart = list(data.get("cart", []))

    name = product.get("title") or product.get("business_name") or "No name"
    price = int(product.get("price_in_app") or product.get("price") or 0)
    branch = product.get("branch_name") or "-"
    distance = round(product.get("distance_km", 0), 2)
    pickup_time = f"{product.get('start_time') or '?'}–{product.get('end_time') or '?'}"
    raw_url = product.get("cover_image")
    image = quote(raw_url, safe=":/") if raw_url else None

    cart.append({
        "category": category,
        "prod_id": prod_id,
        "name": name,
        "price": price,
        "qty": qty,
        "distance": distance,
        "pickup_time": pickup_time,
        "branch": branch,
        "image": image,
    })

    await state.update_data(cart=cart)

    total_price = price * qty
    text = (
        f"{get_localized_text(lang, 'cart.added')}\n\n"
        f"{name}\n"
        f"{get_localized_text(lang, 'cart.total')}: {total_price:,} so‘m"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text=get_localized_text(lang, "cart.view"), callback_data="cart")
    kb.button(text=get_localized_text(lang, "menu.back_to_catalog"), callback_data="back_to_catalog")
    kb.adjust(2)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(text, reply_markup=kb.as_markup())



# ====================== View Cart ======================
@router.callback_query(F.data == "cart")
async def view_cart(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    async with async_session() as db:
        lang = await get_user_lang(db, callback.from_user.id)

    data = await state.get_data()
    cart = data.get("cart", [])

    if not cart:
        kb = InlineKeyboardBuilder()
        kb.button(text=get_localized_text(lang, "menu.catalog"), callback_data="catalog")
        kb.button(text=get_localized_text(lang, "menu.main"), callback_data="back_to_main_menu")
        kb.adjust(2)
        await callback.message.answer(
            f"{get_localized_text(lang, 'cart.empty')}\n{get_localized_text(lang, 'cart.empty_hint')}",
            reply_markup=kb.as_markup()
        )
        return

    total = 0
    text = f"{get_localized_text(lang, 'cart.title')}:\n"
    for i, item in enumerate(cart, 1):
        item_total = item["price"] * item["qty"]
        total += item_total
        text += f"{i}) {item['name']} (x{item['qty']}) - {item_total:,} so‘m\n"
    text += f"\n—\n{get_localized_text(lang, 'cart.grand_total')}: {total:,} so‘m"

    kb = InlineKeyboardBuilder()
    for i in range(1, len(cart) + 1):
        kb.button(text=str(i), callback_data=f"cart_item_{i}")

    kb.button(text=get_localized_text(lang, "cart.checkout"), callback_data="checkout")
    kb.button(text=get_localized_text(lang, "cart.clear"), callback_data="cart_clear")
    kb.button(text=get_localized_text(lang, "menu.main"), callback_data="back_to_main_menu")
    kb.adjust(len(cart), 2, 1)

    try:
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup())


# ====================== Clear Cart ======================
@router.callback_query(F.data == "cart_clear")
async def clear_cart(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(cart=[])
    await view_cart(callback, state)


# ====================== Back to Catalog ======================
@router.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    async with async_session() as db:
        lang = await get_user_lang(db, callback.from_user.id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await show_catalog_menu(callback.message, lang)


# ====================== View Single Cart Item ======================
@router.callback_query(F.data.startswith("cart_item_"))
async def view_cart_item(
    callback: CallbackQuery,
    state: FSMContext,
    idx: int | None = None,
    redraw: bool = False
):
    await callback.answer()
    data = await state.get_data()
    cart = data.get("cart", [])

    async with async_session() as db:
        lang = await get_user_lang(db, callback.from_user.id)

    if idx is None:
        idx = int(callback.data.split("_")[-1]) - 1

    if idx < 0 or idx >= len(cart):
        await callback.answer(get_localized_text(lang, "product.not_found"), show_alert=True)
        return

    item = cart[idx]
    total_price = item["price"] * item["qty"]

    text = (
        f"🍱 {item['name']}\n"
        f"{get_localized_text(lang, 'product.price')}: {total_price:,} so‘m\n"
        f"{get_localized_text(lang, 'product.quantity')}: x{item['qty']}\n"
    )
    if item.get("distance"):
        text += f"{get_localized_text(lang, 'product.distance')}: {item['distance']} km\n"
    if item.get("pickup_time"):
        text += f"{get_localized_text(lang, 'product.pickup_time')}: {item['pickup_time']}\n"
    if item.get("rating"):
        text += f"{get_localized_text(lang, 'product.rating')}: {item['rating']}\n"
    if item.get("branch"):
        text += f"{get_localized_text(lang, 'product.branch')}: {item['branch']}\n"

    kb = InlineKeyboardBuilder()
    kb.button(text=get_localized_text(lang, "product.increase"), callback_data=f"cart_inc_{idx}")
    kb.button(text=get_localized_text(lang, "product.decrease"), callback_data=f"cart_dec_{idx}")
    kb.button(text=get_localized_text(lang, "cart.delete"), callback_data=f"cart_del_{idx}")
    kb.button(text=get_localized_text(lang, "cart.view"), callback_data="cart")
    kb.adjust(2, 2)

    image = item.get("image")

    try:
        if redraw:
            if image:
                await callback.message.edit_media(
                    media=types.InputMediaPhoto(media=image, caption=text),
                    reply_markup=kb.as_markup()
                )
            else:
                await callback.message.edit_text(text, reply_markup=kb.as_markup())
        else:
            try:
                await callback.message.delete()
            except Exception as e:
                print("DELETE ERROR:", e)

            if image:
                await callback.message.answer_photo(
                    photo=image,
                    caption=text,
                    reply_markup=kb.as_markup()
                )
            else:
                await callback.message.answer(text, reply_markup=kb.as_markup())
    except Exception as e:
        print("CART ITEM ERROR:", e)
        if image:
            await callback.message.answer_photo(
                photo=image,
                caption=text,
                reply_markup=kb.as_markup()
            )
        else:
            await callback.message.answer(text, reply_markup=kb.as_markup())




# ====================== Increase / Decrease Quantity ======================
@router.callback_query(F.data.startswith("cart_inc_"))
async def cart_increase(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[-1])
    data = await state.get_data()
    cart = list(data.get("cart", []))

    async with async_session() as db:
        lang = await get_user_lang(db, callback.from_user.id)

    if 0 <= idx < len(cart):
        cart[idx]["qty"] = cart[idx].get("qty", 1) + 1
        await state.update_data(cart=cart)

    await view_cart_item(callback, state, idx, redraw=True)


@router.callback_query(F.data.startswith("cart_dec_"))
async def cart_decrease(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[-1])
    data = await state.get_data()
    cart = list(data.get("cart", []))

    async with async_session() as db:
        lang = await get_user_lang(db, callback.from_user.id)

    if 0 <= idx < len(cart):
        qty = cart[idx].get("qty", 1)
        if qty > 1:
            cart[idx]["qty"] = qty - 1
            await state.update_data(cart=cart)
            await view_cart_item(callback, state, idx, redraw=True)
    else:
        await callback.answer(get_localized_text(lang, "cart.warning"))


# ====================== Delete Confirmation ======================
@router.callback_query(F.data.regexp(r"^cart_del_\d+$"))
async def cart_delete_confirm(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[-1])
    data = await state.get_data()
    cart = data.get("cart", [])

    async with async_session() as db:
        lang = await get_user_lang(db, callback.from_user.id)

    if 0 <= idx < len(cart):
        item = cart[idx]
        name = item["name"]
        text = (
            f"“{name}” {get_localized_text(lang, 'cart.delete_confirm')}\n"
            f"{get_localized_text(lang, 'cart.no_undo')}"
        )

        kb = InlineKeyboardBuilder()
        kb.button(text=get_localized_text(lang, "cart.delete_yes"), callback_data=f"cart_del_yes_{idx}")
        kb.button(text=get_localized_text(lang, "cart.delete_no"), callback_data="cart_del_no")
        kb.adjust(2)

        if callback.message.content_type == "text":
            if callback.message.text != text:
                await callback.message.edit_text(text, reply_markup=kb.as_markup())
            else:
                await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
        elif callback.message.content_type == "photo":
            if callback.message.caption != text:
                await callback.message.edit_caption(caption=text, reply_markup=kb.as_markup())
            else:
                await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
        else:
            await callback.message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("cart_del_yes_"))
async def cart_delete_yes(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[-1])
    data = await state.get_data()
    cart = data.get("cart", [])
    if 0 <= idx < len(cart):
        cart.pop(idx)
        await state.update_data(cart=cart)
    await view_cart(callback, state)


@router.callback_query(F.data == "cart_del_no")
async def cart_delete_no(callback: CallbackQuery, state: FSMContext):
    await view_cart(callback, state)
