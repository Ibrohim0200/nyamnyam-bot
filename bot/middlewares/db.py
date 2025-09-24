from aiogram import BaseMiddleware
from bot.database.db_config import async_session_maker


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with async_session_maker() as session:
            data["session"] = session
            return await handler(event, data)
