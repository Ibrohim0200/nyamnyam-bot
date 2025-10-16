import asyncio

import httpx
from aiogram import Router, F, types
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from urllib.parse import quote

from api.product_api import fetch_surprise_bag, fetch_surprise_bag_by_category
from bot.keyboards.catalog_keyboard import catalog_menu_keyboard
from bot.locale.get_lang import get_localized_text
from bot.keyboards.start_keyboard import main_menu_keyboard
from bot.keyboards.product_keyboard import products_pagination_keyboard
from bot.database.views import get_user_lang
from bot.database.db_config import async_session

router = Router()


ITEMS_PER_PAGE = 5

def extract_category_and_id(data: str, start_index: int):
    parts = data.split("_")
    category = "_".join(parts[start_index:-1])
    prod_id = int(parts[-1])
    return category, prod_id



async def _is_image_url(url: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.head(url, timeout=5.0, follow_redirects=True)
            ct = (resp.headers.get("content-type") or "").lower()
            if resp.status_code == 200 and ct.startswith("image/"):
                return True
            resp = await client.get(url, timeout=5.0, follow_redirects=True)
            ct = (resp.headers.get("content-type") or "").lower()
            return resp.status_code == 200 and ct.startswith("image/")
    except Exception:
        return False

async def show_products(message: Message, category: str, page: int, state: FSMContext, callback_query: CallbackQuery = None):
    user_id = message.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)

    try:
        if category == "superbox":
            data = await state.get_data()
            items = data.get("superbox_items", [])
            await state.update_data(superbox_items=items)
        else:
            slug = category.replace(" ", "-").lower()
            items = await fetch_surprise_bag_by_category(slug)
            await state.update_data(**{f"{category.lower()}_items": items})
    except Exception as e:
        await message.answer(get_localized_text(lang, "catalog.fetch_error") + f"\n`{e}`")
        return
    if not items:
        text_empty = get_localized_text(lang, "catalog.empty")
        await message.answer(text_empty, reply_markup=main_menu_keyboard(lang, user_id))
        return
    total_pages = (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = max(1, min(page, total_pages))
    start, end = (page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE
    page_items = items[start:end]

    title_tpl = get_localized_text(lang, "catalog.category_title") or "{cat}"
    page_tpl = get_localized_text(lang, "pagination.page") or "{page}"
    text = f"{title_tpl.replace('{cat}', category.capitalize())} ({page_tpl.replace('{page}', str(page))}):\n\n"

    for idx, product in enumerate(page_items, start=start + 1):
        title = product.get("title") or product.get("name") or "No name"
        business = product.get("business_name", "-") or "No business"
        branch = product.get("branch_name", "-") or "No branch"
        price = product.get("price_in_app") or product.get("price") or 0
        currency = product.get("currency", "so‘m")
        distance = round(product.get("distance_km", 0), 2)

        text += (
            f"{idx}) 🏪 {business} ({branch})\n"
            f"📦 {title}\n"
            f"💰 {price} {currency}\n"
            f"📍 {get_localized_text(lang, 'product.distance')}: {distance} km\n\n"
        )

    markup = products_pagination_keyboard(lang, category, page, total_pages)
    if callback_query:
        try:
            await message.edit_text(text, reply_markup=markup)
        except Exception:
            await message.answer(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)




async def show_product_detail(
    callback: CallbackQuery,
    state: FSMContext,
    category: str,
    prod_id: int,
    redraw: bool = False,
    force_edit: bool = False
):
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)

    data = await state.get_data()
    key = "superbox_items" if category == "superbox" else f"{category.lower()}_items"
    items = data.get(key, [])


    if not redraw:
        try:
            await callback.message.delete()
        except Exception as e:
            print("DELETE ERROR:", e)

    if not items or prod_id < 1 or prod_id > len(items):
        await callback.answer(get_localized_text(lang, "product.not_found"), show_alert=True)
        return

    product = items[prod_id - 1]
    qty_data = data.get("qty_temp", {})
    qty = qty_data.get(f"{category}_{prod_id}", 1)

    title = product.get("title") or product.get("name") or "No name"
    branch = product.get("branch_name") or "-"
    price = int(product.get("price_in_app") or product.get("price") or 0)
    currency = product.get("currency", "so‘m")
    distance_str = product.get("distance", "0").split()[0]
    try:
        distance = round(float(distance_str), 2)
    except:
        distance = 0.0
    start_time = product.get("start_time") or "?"
    end_time = product.get("end_time") or "?"
    raw_url = product.get("cover_image")
    image = quote(raw_url, safe=":/") if raw_url else None
    total_price = price * qty

    text = (
        f"🍔 {title}\n"
        f"{get_localized_text(lang, 'product.price')}: {total_price} {currency}\n"
        f"{get_localized_text(lang, 'product.quantity')}: x{qty}\n"
        f"{get_localized_text(lang, 'product.distance')}: {distance} km\n"
        f"{get_localized_text(lang, 'product.rating')}: ⭐️5.0\n"
        f"{get_localized_text(lang, 'product.pickup_time')}: {start_time}–{end_time}\n"
        f"{get_localized_text(lang, 'product.branch')}: {branch}"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text=get_localized_text(lang, "product.increase"), callback_data=f"qty_inc_{category}_{prod_id}")
    kb.button(text=get_localized_text(lang, "product.decrease"), callback_data=f"qty_dec_{category}_{prod_id}")
    kb.button(text=get_localized_text(lang, "product.add_to_cart"), callback_data=f"cart_add_{category}_{prod_id}")
    kb.button(text=get_localized_text(lang, "product.back_to_list"), callback_data=f"cat_{category}")
    kb.adjust(2, 2)


    if image and await _is_image_url(image):
        try:
            if force_edit or (callback.message.photo and image):
                await callback.message.edit_media(
                    media=types.InputMediaPhoto(media=image, caption=text),
                    reply_markup=kb.as_markup()
                )
            else:
                await callback.bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=image,
                    caption=text,
                    reply_markup=kb.as_markup()
                )
        except Exception as e:
            print("MEDIA ERROR:", e)
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=image,
                caption=text,
                reply_markup=kb.as_markup()
            )

# CALLBACKS

@router.callback_query(F.data.startswith("product_"))
async def product_detail(callback: CallbackQuery, state: FSMContext):
    category, prod_id = extract_category_and_id(callback.data, 1)
    await show_product_detail(callback, state, category, prod_id, redraw=False)


@router.callback_query(F.data.startswith("qty_inc_"))
async def increase_qty(callback: CallbackQuery, state: FSMContext):
    category, prod_id = extract_category_and_id(callback.data, 2)
    data = await state.get_data()
    qty_data = dict(data.get("qty_temp", {}))
    key = f"{category}_{prod_id}"
    qty_data[key] = qty_data.get(key, 1) + 1
    await state.update_data(qty_temp=qty_data)
    await show_product_detail(callback, state, category, prod_id, redraw=True, force_edit=True)


@router.callback_query(F.data.startswith("qty_dec_"))
async def decrease_qty(callback: CallbackQuery, state: FSMContext):
    category, prod_id = extract_category_and_id(callback.data, 2)
    data = await state.get_data()
    qty_data = dict(data.get("qty_temp", {}))
    key = f"{category}_{prod_id}"
    qty = qty_data.get(key, 1)
    if qty > 1:
        qty_data[key] = qty - 1
        await state.update_data(qty_temp=qty_data)
        await show_product_detail(callback, state, category, prod_id, redraw=True, force_edit=True)
    else:
        await callback.answer("❗ Minimal miqdor 1 ta", show_alert=False)




@router.callback_query(F.data == "cat_surprise_bag")
async def show_superbox(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    try:
        data = await fetch_surprise_bag()
        print("🔍 SUPERBOX RESPONSE:", data)
    except Exception as e:
        await callback.message.answer(
            get_localized_text(lang, "catalog.fetch_error") + f"\n`{e}`"
        )
        return

    if not data:
        await callback.message.answer(get_localized_text(lang, "catalog.empty_superbox"))
        return

    builder = InlineKeyboardBuilder()
    for section, items in data.items():
        if len(items) < 1:
            continue
        localized = get_localized_text(lang, f"catalog.section_{section}")
        section_title = localized if localized else section.capitalize()
        builder.button(text=section_title, callback_data=f"superbox_section_{section}")
    builder.button(
        text=get_localized_text(lang, "menu.back_to_catalog"),
        callback_data="back_to_catalog"
    )
    builder.adjust(2)

    if not builder.buttons:
        await callback.message.answer(get_localized_text(lang, "catalog.empty_superbox"))
        return

    await state.update_data(superbox_full_data=data)
    await callback.message.answer(
        get_localized_text(lang, "catalog.choose_superbox_section"),
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("superbox_section_"))
async def show_superbox_section(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)

    section = callback.data.split("superbox_section_")[1]
    data = await state.get_data()
    superbox_full_data = data.get("superbox_full_data", {})

    items = superbox_full_data.get(section, [])
    if not items:
        await callback.message.answer(f"❌ '{section}' bo‘limida mahsulot topilmadi.")
        return

    await state.update_data(superbox_items=items)


    await show_products(
        callback.message,
        "superbox",
        page=1,
        state=state,
        callback_query=callback
    )






@router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: CallbackQuery, state: FSMContext):
    category_slug = callback.data.split("_", 1)[1]
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    await show_products(callback.message, category_slug, page=1, state=state)



@router.callback_query(F.data.startswith("page_"))
async def change_page(callback: CallbackQuery, state: FSMContext):
    _, category, page_str = callback.data.split("_", 2)
    try:
        page = int(page_str)
    except ValueError:
        async with async_session() as db:
            lang = await get_user_lang(db, callback.from_user.id)
        await callback.answer(get_localized_text(lang, "pagination.invalid"), show_alert=True)
        return
    await callback.answer()
    await callback.message.delete()
    await show_products(callback.message, category, page, state=state, callback_query=callback)


@router.callback_query(F.data.startswith("back_list_"))
async def back_to_list(callback: CallbackQuery, state: FSMContext):
    _, _, category, page_str = callback.data.split("_", 3)
    page = int(page_str)
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)
    await callback.answer()
    await callback.message.delete()
    await show_products(callback.message, category, page, state=state)


@router.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session() as db:
        lang = await get_user_lang(db, user_id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        get_localized_text(lang, "catalog.choose_category"),
        reply_markup=await catalog_menu_keyboard(lang)
    )
    await callback.answer()
