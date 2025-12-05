import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers import menu_handler, profile_handler, language_handler, orders_handler, register_handler
from bot.handlers import start_handler, catalog_handler, product_handler, cart_handler, order_handler
from bot.config.env import BOT_TOKEN
from aiogram.types import BotCommand

from bot.middlewares.db import DbSessionMiddleware
from aiogram.exceptions import TelegramBadRequest

async def safe_delete(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="menu", description="🏠 Asosiy menyu"),
        BotCommand(command="profile", description="👤 Profilni ko‘rish"),
        BotCommand(command="login", description="🔑 Tizimga kirish"),
        BotCommand(command="register", description="📝 Ro‘yxatdan o‘tish"),
    ]
    await bot.set_my_commands(commands)


async def main():
    bot = Bot(token=BOT_TOKEN, default_parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.outer_middleware(DbSessionMiddleware())

    dp.include_router(register_handler.router)
    dp.include_router(start_handler.router)
    dp.include_router(catalog_handler.router)
    dp.include_router(product_handler.router)
    dp.include_router(cart_handler.router)
    dp.include_router(menu_handler.router)
    dp.include_router(profile_handler.router)
    dp.include_router(language_handler.router)
    dp.include_router(orders_handler.router)
    dp.include_router(order_handler.router)

    await set_bot_commands(bot)

    print("Bot started successfully!")

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
