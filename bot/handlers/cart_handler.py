from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.locale.get_lang import get_localized_text
from bot.handlers.product_handler import PRODUCTS

router = Router()
USER_CARTS = {}

def format_cart_text(cart, lang):
    total = 0
    text = get_localized_text(lang, "cart.title") + "\n"
    for category, items in cart.items():
        for prod_id, qty in items.items():
            product = PRODUCTS[category][prod_id]
            price = int(product["price"].replace(" ", "").replace("so‘m", ""))
            total += price * qty
            text += f"{product['name']} ×{qty} — {product['price']}\n"
    text += f"—\n{get_localized_text(lang, 'cart.total')}: {total:,} so‘m"
    return text

@router.callback_query(F.data.startswith("qty_inc_"))
async def increase_qty(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    category = parts[2]
    prod_id = int(parts[3]) - 1

    data = await state.get_data()
    qty_temp = data.get("qty_temp", {})
    key = f"{category}_{prod_id}"

    qty_temp[key] = qty_temp.get(key, 1) + 1
    await state.update_data(qty_temp=qty_temp)

    lang = (await state.get_data()).get("lang", "uz")
    text = await product_text(category, prod_id, qty_temp[key], lang)

    kb = InlineKeyboardBuilder()
    kb.button(text=get_localized_text(lang, "product.add_to_cart"), callback_data=f"cart_add_{category}_{prod_id+1}")
    kb.button(text=get_localized_text(lang, "product.increase"), callback_data=f"qty_inc_{category}_{prod_id+1}")
    kb.button(text=get_localized_text(lang, "product.decrease"), callback_data=f"qty_dec_{category}_{prod_id+1}")
    kb.button(text=get_localized_text(lang, "product.back_to_list"), callback_data=f"cat_{category}")
    kb.adjust(2,2)

    await callback.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("qty_dec_"))
async def decrease_qty(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    category = parts[2]
    prod_id = int(parts[3]) - 1

    data = await state.get_data()
    qty_temp = data.get("qty_temp", {})
    key = f"{category}_{prod_id}"
    current_qty = qty_temp.get(key, 1)

    if current_qty > 1:
        qty_temp[key] = current_qty - 1
    else:
        qty_temp[key] = current_qty

    await state.update_data(qty_temp=qty_temp)

    lang = (await state.get_data()).get("lang", "uz")
    text = await product_text(category, prod_id, qty_temp[key], lang)

    kb = InlineKeyboardBuilder()
    kb.button(text=get_localized_text(lang, "product.add_to_cart"), callback_data=f"cart_add_{category}_{prod_id+1}")
    kb.button(text=get_localized_text(lang, "product.increase"), callback_data=f"qty_inc_{category}_{prod_id+1}")
    kb.button(text=get_localized_text(lang, "product.decrease"), callback_data=f"qty_dec_{category}_{prod_id+1}")
    kb.button(text=get_localized_text(lang, "product.back_to_list"), callback_data=f"cat_{category}")
    kb.adjust(2,2)

    await callback.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("cart_add_"))
async def add_to_cart(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    category = parts[2]
    prod_id = int(parts[3]) - 1

    user_id = callback.from_user.id
    cart = USER_CARTS.setdefault(user_id, {})

    data = await state.get_data()
    qty_temp = data.get("qty_temp", {})
    key = f"{category}_{prod_id}"
    qty_to_add = qty_temp.get(key, 1)

    cat_cart = cart.setdefault(category, {})
    cat_cart[prod_id] = cat_cart.get(prod_id, 0) + qty_to_add

    lang = (await state.get_data()).get("lang", "uz")
    text = f"✅ {PRODUCTS[category][prod_id]['name']} {get_localized_text(lang, 'cart.added')}\n"
    text += format_cart_text(cart, lang)

    kb = InlineKeyboardBuilder()
    kb.button(text=get_localized_text(lang, "cart.view_cart"), callback_data="view_cart")
    kb.button(text=get_localized_text(lang, "menu.back_to_catalog"), callback_data=f"cat_{category}")
    kb.adjust(2)

    await callback.message.edit_text(text, reply_markup=kb.as_markup())

async def product_text(category, prod_id, qty, lang):
    product = PRODUCTS[category][prod_id]
    price = int(product["price"].replace(" ", "").replace("so‘m",""))
    total_price = price * qty
    return (
        f"🍔 {product['name']}\n"
        f"{get_localized_text(lang,'product.price')}: {total_price:,} so‘m\n"
        f"{get_localized_text(lang,'product.quantity')}: x{qty}\n"
        f"{get_localized_text(lang,'product.distance')}: 2.3 km\n"
        f"{get_localized_text(lang,'product.rating')}: {product['rating']}\n"
        f"{get_localized_text(lang,'product.pickup_time')}: 17:00–18:00\n"
        f"{get_localized_text(lang,'product.branch')}: {product['branch']}"
    )
