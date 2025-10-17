from multiprocessing.spawn import set_executable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from bot.database.models import Cart


async def add_to_cart(session: AsyncSession, telegram_id: int, product_id: int, name:str, price: float, quantity: int = 1):
    total_price = price * quantity
    item = Cart(
        telegram_id=telegram_id,
        product_id=product_id,
        product_name = name,
        price = price,
        quantity =quantity,
        total_price=total_price
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item

async def get_cart(session: AsyncSession, telegram_id: int):
    result = await session.execute(
        select(Cart).where(Cart.telegram_id==telegram_id)
    )

    return result.scalars().all()

async def clear_cart(session: AsyncSession, telegram_id :int):
    await session.execute(
        delete(Cart).where(Cart.telegram_id==telegram_id)

    )
    await session.commit()
