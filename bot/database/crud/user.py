from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql.functions import session_user

from bot.database.models import User

async def get_user(session: AsyncSession, telegram_id: int):
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()

async def create_user(session: AsyncSession, telegram_id: int, full_name: str = None, phone: str = None, email: str = None):
    user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        phone=phone,
        email=email
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def update_user(session: AsyncSession, telegram_id: int, **kwargs):
    user = await get_user(session, telegram_id)
    if not user:
        return None
    for field, value in kwargs.items():
        if hasattr(user, field) and value is not None:
            setattr(user, field, value)

        await session.commit()
        await session.refresh(user)
        return user


