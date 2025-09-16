import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers import start_handler, catalog_handler, product_handler, cart_handler, menu_handler
from bot.database.create_tables import create_tables
from bot.config.env import BOT_TOKEN
from aiogram.types import BotCommand


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
    ]
    await bot.set_my_commands(commands)


async def main():
    await create_tables()
    bot = Bot(token=BOT_TOKEN, default_parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(start_handler.router)
    dp.include_router(catalog_handler.router)
    dp.include_router(product_handler.router)
    dp.include_router(cart_handler.router)
    dp.include_router(menu_handler.router)

    await set_bot_commands(bot)

    print("Bot started successfully!")

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
