import httpx
import os

from aiogram.types import Message
from dotenv import load_dotenv
from sqlalchemy import select

from bot.database.db_config import async_session_maker
from bot.database.models import UserTokens
from bot.database.views import get_user_lang
from bot.locale.get_lang import get_localized_text

load_dotenv()

BASE_URL = os.getenv("BASE_URL")


async def send_register_data(payload: dict, is_email: bool):
    url = f"{BASE_URL}users/auth/register/"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
    try:
        data = resp.json()
    except:
        data = {"success": False, "message": "Invalid JSON from server"}

    return {
        "status": resp.status_code,
        "success": resp.status_code in [200, 201],
        "otp_sent": data.get("otp_sent"),
        "message": data.get("message"),
        "raw": data
    }


async def send_login_data(payload: dict):
    url = f"{BASE_URL}users/auth/login/"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def verify_otp(payload: dict):
    url = f"{BASE_URL}users/otp/verify"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=payload)
        except Exception as e:
            return {
                "success": False,
                "status": 0,
                "message": str(e),
            }
    try:
        data = resp.json()
    except:
        return {
            "success": False,
            "status": resp.status_code,
            "message": resp.text
        }
    if resp.status_code == 200:
        return {
            "success": True,
            "status": 200,
            "data": data
        }
    return {
        "success": False,
        "status": resp.status_code,
        "message": data.get("error_message") or data.get("message") or resp.text,
        "raw": data
    }

async def set_user_password(id: str, password: str, first_name: str | None = None):
    url = f"{BASE_URL}users/auth/{id}/update_detail/"
    payload = {"password": password}
    if first_name:
        payload["first_name"] = first_name
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.patch(url, json=payload)
        except Exception as e:
            return {"success": False, "status": 0, "message": str(e)}
    try:
        data = resp.json()
    except Exception:
        data = None
    if resp.status_code in (200, 201):
        return {
            "success": True,
            "status": resp.status_code,
            "raw": data
        }
    message = None
    if isinstance(data, dict):
        message = (
            data.get("message")
            or data.get("error_message")
            or data.get("detail")
            or str(data)
        )
    else:
        message = resp.text
    return {
        "success": False,
        "status": resp.status_code,
        "message": message,
        "raw": data
    }


async def get_tokens_by_user_id(chat_id: int):
    url = f"{BASE_URL}users/auth/user_by_chat/{chat_id}/"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
    try:
        data = resp.json()
    except:
        return {"success": False, "message": "Invalid JSON"}

    if not data.get("success"):
        return {"success": False, "message": data.get("message")}
    tokens = data.get("data", {}).get("message", {})
    return {
        "success": True,
        "access": tokens.get("access_token"),
        "refresh": tokens.get("refresh_token"),
    }



async def get_user_profile(access_token: str):
    url = f"{BASE_URL}users/auth/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def update_user_profile(access_token: str, data: dict):
    url = f"{BASE_URL}users/auth/update-me/"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        response = await client.patch(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()



async def post_order(access_token: str, items: list, payment_method: str):
    import httpx
    payload = {
        "order_items": items,
        "total_price": sum(int(item["price"]) * int(item["count"]) for item in items),
        "payment_method": payment_method
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    url = f"{BASE_URL}users/order/"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return {"success": False, "status": e.response.status_code, "error": e.response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_valid_access_token(user_id: int, event):
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserTokens).where(UserTokens.telegram_id == user_id)
        )
        tokens = result.scalar_one_or_none()

        lang = await get_user_lang(user_id)

        if not tokens or not tokens.access_token:
            await event.answer(get_localized_text(lang, "profile.no_token"))
            return None

        access_token = tokens.access_token

        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                check = await client.get(f"{BASE_URL}user/me/", headers=headers)

            if check.status_code == 401:
                refreshed = await refresh_access_token(user_id)

                if refreshed.get("success"):
                    return refreshed["access_token"]

                await event.answer(get_localized_text(lang, "profile.token_expired"))
                return None

            elif check.status_code == 200:
                return access_token

            else:
                await event.answer(
                    f"❌ {get_localized_text(lang, 'profile.error').format(error=check.text)}"
                )
                return None

        except Exception as e:
            return None


async def refresh_access_token(user_id: int):
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserTokens).where(UserTokens.telegram_id == user_id)
        )
        user_token = result.scalar_one_or_none()
        if not user_token or not user_token.refresh_token:
            return {"success": False, "error": "No refresh token found"}
        url = f"{BASE_URL}users/auth/refresh-token/"
        payload = {"refresh": user_token.refresh_token}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
            if response.status_code != 200:
                return {"success": False, "error": response.text}
            raw = response.json()
            data = raw.get("data", {})
            new_access = data.get("access_token")
            new_refresh = data.get("refresh_token")
            if not new_access:
                return {"success": False, "error": "Access token not found"}

            user_token.access_token = new_access
            if new_refresh:
                user_token.refresh_token = new_refresh
            await session.commit()

            return {
                "success": True,
                "access_token": new_access,
                "refresh_token": new_refresh
            }

        except Exception as e:
            return {"success": False, "error": str(e)}



async def fetch_orders_from_api(user_token: str):
    url = f"{BASE_URL}users/order/my_last_orders/"
    headers = {"Authorization": f"Bearer {user_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        data = response.json()

        if not data.get("success"):
            return []

        return data["data"]


async def fetch_order_history(token: str):
    url = f"{BASE_URL}users/order/my_orders/"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict) or "data" not in data:
        return []
    orders = data["data"]
    if not isinstance(orders, list):
        return []
    return orders