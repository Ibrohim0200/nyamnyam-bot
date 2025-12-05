from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from .db_config import async_session_maker
from .models import UserLang, UserTokens
from sqlalchemy.future import select

async def get_user_lang(telegram_id: int) -> str:
    async with async_session_maker() as db:
        result = await db.execute(select(UserLang).where(UserLang.telegram_id == telegram_id))
        user_lang = result.scalar_one_or_none()
        return user_lang.lang if user_lang else "uz"


async def set_user_lang(telegram_id: int, lang: str):
    async with async_session_maker() as db:
        result = await db.execute(select(UserLang).where(UserLang.telegram_id == telegram_id))
        user_lang = result.scalar_one_or_none()
        if user_lang:
            user_lang.lang = lang
        else:
            db.add(UserLang(telegram_id=telegram_id, lang=lang))
        await db.commit()

async def save_user_tokens(db: AsyncSession, telegram_id: int, access_token: str, refresh_token: str):
    result = await db.execute(select(UserTokens).where(UserTokens.telegram_id == telegram_id))
    existing = result.scalar_one_or_none()

    if existing:
        existing.access_token = access_token
        existing.refresh_token = refresh_token
        existing.created_at = datetime.utcnow()
    else:
        db.add(UserTokens(
            telegram_id=telegram_id,
            access_token=access_token,
            refresh_token=refresh_token,
            created_at=datetime.utcnow()
        ))

    await db.commit()