from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.models import UserTokens



async def create_or_update_token(session: AsyncSession, telegram_id: int, access: str, refresh: str):
    result = await session.execute(
        select(UserTokens).where(UserTokens.telegram_id ==telegram_id)

    )
    tokens = result.scalar_one_ot_none()

    if tokens:
        tokens.access_token = access
        tokens.refresh_token = refresh
    else:
        tokens = UserTokens(
            telegram_id=telegram_id,
            access_token=access,
            refresh_token=refresh
        )
        session.add(tokens)

    await session.commit()
    await session.refresh(tokens)
    return tokens

async def get_tokens(session: AsyncSession, telegram_id:int):
    result = await session.execute(
        select(UserTokens).where(UserTokens.telegram_id == telegram_id)

    )
    return result.scalar_one_or_none()