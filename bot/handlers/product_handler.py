from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api.product_api import fetch_surprise_bag
from bot.locale.get_lang import get_localized_text
from bot.keyboards.start_keyboard import main_menu_keyboard
from bot.keyboards.product_keyboard import products_pagination_keyboard

router = Router()

# Vaqtinchalik productlar (API keyin qo‘shiladi)
PRODUCTS = {
    "fastfood": [
        {"name": "Surprise bag", "price": "12 000 so‘m", "rating": "⭐5.0", "branch": "Chilonzor"},
        {"name": "Burger set", "price": "25 000 so‘m", "rating": "⭐4.8", "branch": "Yunusobod"},
        {"name": "Pitsa box", "price": "30 000 so‘m", "rating": "⭐4.9", "branch": "Olmazor"},
        {"name": "Lavash maxsus", "price": "18 000 so‘m", "rating": "⭐4.7", "branch": "Sergeli"},
        {"name": "Salat mix", "price": "15 000 so‘m", "rating": "⭐4.6", "branch": "Chilonzor"},
        {"name": "Hot-dog max", "price": "14 000 so‘m", "rating": "⭐4.5", "branch": "Chilonzor"},
        {"name": "Fri kartoshka", "price": "10 000 so‘m", "rating": "⭐4.3", "branch": "Yunusobod"},
    ]
}

ITEMS_PER_PAGE = 5


# 📦 Surprise Bag ro‘yxatini ko‘rsatish (API dan keladi)
@router.callback_query(F.data == "cat_superbox")
async def show_superbox(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "uz")
    await callback.answer()

    try:
        items = await fetch_surprise_bag()
    except Exception as e:
        await callback.message.answer(get_localized_text(lang, "catalog.fetch_error") + f"\n`{e}`")
        return

    if not items:
        await callback.message.answer(get_localized_text(lang, "catalog.empty"))
        return

    await state.update_data(superbox_items=items)  # statega saqlaymiz
    await show_products(callback.message, "superbox", page=1, lang=lang, state=state, callback_query=callback)


# 🥡 Oddiy kategoriyalar (fastfood va boshqalar)
@router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_", 1)[1]
    lang = (await state.get_data()).get("lang", "uz")
    await show_products(callback.message, category, page=1, lang=lang, state=state, callback_query=callback)


# 🔄 Paginatsiya tugmalari
@router.callback_query(F.data.startswith("page_"))
async def change_page(callback: CallbackQuery, state: FSMContext):
    _, category, page_str = callback.data.split("_", 2)
    try:
        page = int(page_str)
    except ValueError:
        await callback.answer(get_localized_text("uz", "pagination.invalid"), show_alert=True)
        return

    lang = (await state.get_data()).get("lang", "uz")
    await show_products(callback.message, category, page, lang, state=state, callback_query=callback)
    await callback.answer()


# 📄 Mahsulotlar ro‘yxatini ko‘rsatish
async def show_products(message: Message, category: str, page: int, lang: str, state: FSMContext, callback_query: CallbackQuery = None):
    # Superbox API bo‘lsa state’dan olish
    if category == "superbox":
        data = await state.get_data()
        items = data.get("superbox_items", [])
    else:
        items = PRODUCTS.get(category, [])

    if not items:
        text_empty = get_localized_text(lang, "catalog.empty") or "Bu kategoriyada mahsulotlar topilmadi."
        if callback_query:
            await message.edit_text(text_empty, reply_markup=main_menu_keyboard())
        else:
            await message.answer(text_empty, reply_markup=main_menu_keyboard())
        return

    total_pages = (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = max(1, min(page, total_pages))
    start, end = (page - 1) * ITEMS_PER_PAGE, (page - 1) * ITEMS_PER_PAGE + ITEMS_PER_PAGE
    page_items = items[start:end]

    # Matn yasash
    title_tpl = get_localized_text(lang, "catalog.category_title") or "{cat} kategoriyasi"
    text = f"{title_tpl.replace('{cat}', category.capitalize())} ({page}-sahifa):\n\n"

    for idx, product in enumerate(page_items, start=start + 1):
        if category == "superbox":
            title = product.get("title") or "Nomi yo‘q"
            business = product.get("business_name") or "Noma’lum"
            branch = product.get("branch_name") or "-"
            price = product.get("price_in_app") or product.get("price") or 0
            currency = product.get("currency", "so‘m")
            distance = round(product.get("distance_km", 0), 2)
            text += (
                f"{idx}) 🏪 {business} ({branch})\n"
                f"📦 {title}\n"
                f"💰 {price} {currency}\n"
                f"📍 Masofa: {distance} km\n\n"
            )
        else:
            text += f"{idx}) {product['name']} — {product['price']} {product['rating']}\n"

    # Inline keyboard (universal)
    markup = products_pagination_keyboard(lang, category, page, total_pages)

    if callback_query:
        try:
            await message.edit_text(text, reply_markup=markup)
        except Exception:
            await message.answer(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


# 📦 Mahsulot tafsiloti (detail)
@router.callback_query(F.data.startswith("product_"))
async def product_detail(callback: CallbackQuery, state: FSMContext):
    _, category, prod_id_str = callback.data.split("_", 2)
    prod_id = int(prod_id_str)

    if category == "superbox":
        data = await state.get_data()
        items = data.get("superbox_items", [])
    else:
        items = PRODUCTS.get(category, [])

    if prod_id < 1 or prod_id > len(items):
        lang = (await state.get_data()).get("lang", "uz")
        await callback.answer(get_localized_text(lang, "product.not_found"), show_alert=True)
        return

    product = items[prod_id - 1]
    lang = (await state.get_data()).get("lang", "uz")

    if category == "superbox":
        title = product.get("title") or "Nomi yo‘q"
        branch = product.get("branch_name") or "-"
        price = product.get("price_in_app") or product.get("price") or 0
        currency = product.get("currency", "so‘m")
        distance = round(product.get("distance_km", 0), 2)
        start_time = product.get("start_time") or "?"
        end_time = product.get("end_time") or "?"
        image = product.get("cover_image")

        text = (
            f"🍔 {title}\n"
            f"{get_localized_text(lang,'product.price')}: {price} {currency}\n"
            f"{get_localized_text(lang,'product.quantity')}: x1\n"
            f"{get_localized_text(lang,'product.distance')}: {distance} km\n"
            f"{get_localized_text(lang,'product.rating')}: ⭐️5.0\n"
            f"{get_localized_text(lang,'product.pickup_time')}: {start_time}–{end_time}\n"
            f"{get_localized_text(lang,'product.branch')}: {branch}"
        )

        kb = InlineKeyboardBuilder()
        kb.button(text=get_localized_text(lang, "product.add_to_cart"), callback_data=f"cart_add_superbox_{prod_id}")
        kb.button(text=get_localized_text(lang, "product.back_to_list"), callback_data="cat_superbox")
        kb.adjust(1, 1)

        if image:
            await callback.message.answer_photo(photo=image, caption=text, reply_markup=kb.as_markup())
        else:
            await callback.message.answer(text, reply_markup=kb.as_markup())

    else:  # fastfood, drinks va hokazo
        data = await state.get_data()
        qty_data = data.get("qty_temp", {})
        qty = qty_data.get(f"{category}_{prod_id}", 1)

        text = (
            f"🍔 {product['name']}\n"
            f"{get_localized_text(lang,'product.price')}: {product['price']}\n"
            f"{get_localized_text(lang,'product.quantity')}: x{qty}\n"
            f"{get_localized_text(lang,'product.distance')}: 2.3 km\n"
            f"{get_localized_text(lang,'product.rating')}: {product['rating']}\n"
            f"{get_localized_text(lang,'product.pickup_time')}: 17:00–18:00\n"
            f"{get_localized_text(lang,'product.branch')}: {product['branch']}"
        )

        kb = InlineKeyboardBuilder()
        kb.button(text=get_localized_text(lang, "product.add_to_cart"), callback_data=f"cart_add_{category}_{prod_id}")
        kb.button(text=get_localized_text(lang, "product.increase"), callback_data=f"qty_inc_{category}_{prod_id}")
        kb.button(text=get_localized_text(lang, "product.decrease"), callback_data=f"qty_dec_{category}_{prod_id}")
        kb.button(text=get_localized_text(lang, "product.back_to_list"), callback_data=f"cat_{category}")
        kb.adjust(2, 2)

        await callback.message.edit_text(text, reply_markup=kb.as_markup())
