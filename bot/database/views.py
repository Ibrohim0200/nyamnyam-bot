from sqlalchemy.ext.asyncio import AsyncSession
from .models import UserLang
from sqlalchemy.future import select

async def get_user_lang(db: AsyncSession, telegram_id: int) -> str:
    result = await db.execute(select(UserLang).where(UserLang.telegram_id == telegram_id))
    user_lang = result.scalar_one_or_none()
    if user_lang:
        return user_lang.lang
    return "uz"

async def set_user_lang(db: AsyncSession, telegram_id: int, lang: str):
    result = await db.execute(select(UserLang).where(UserLang.telegram_id == telegram_id))
    user_lang = result.scalar_one_or_none()
    if user_lang:
        user_lang.lang = lang
    else:
        user_lang = UserLang(telegram_id=telegram_id, lang=lang)
        db.add(user_lang)
    await db.commit()