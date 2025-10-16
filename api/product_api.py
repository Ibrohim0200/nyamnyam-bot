import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")

async def fetch_surprise_bag():
    url = f"{BASE_URL}bot/surprise-bag/"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {})

async def fetch_categories():
    url = f"{BASE_URL}bot/category/"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])


async def fetch_surprise_bag_by_category(slug: str):
    slug = slug.replace(" ", "-").lower()
    url = f"{BASE_URL}bot/surprise-bag/category/?slug={slug}"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10.0)
            data = resp.json()
            value = data.get("data", None)
            return value if isinstance(value, list) else []
        except Exception as e:
            print(f"❌ HTTP xato: {e}")
            return []
