from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql.functions import session_user

from bot.database.models import UserLang


async def create_user_lang(session: AsyncSession, telegram_id: int, lang: str = "uz"):
    user = UserLang(telegram_id=telegram_id, lang=lang)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def get_user_lang(session: AsyncSession, telegram_id: int):
    result = await session.execute(
        select(UserLang).where(UserLang.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def update_user_lang(session: AsyncSession, telegram_id: int, new_lang:str):
    user = await get_user_lang(session, telegram_id)
    if user:
        user.lang = new_lang
        await session.commit()
        await session.refresh(user)

    return user