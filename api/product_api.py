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
        return data.get("data", [])

