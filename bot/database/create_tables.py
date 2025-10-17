from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from bot.database.db_config import engine, Base
from bot.database.models import UserLang, UserTokens, Cart, User, Order


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Языки
        user_lang1 = UserLang(telegram_id=1888565858, lang="en")
        user_lang2 = UserLang(telegram_id=1888563858, lang="ru")

        # Токены
        token1 = UserTokens(telegram_id=1888565858, access_token="access123", refresh_token="refresh123")
        token2 = UserTokens(telegram_id=1888563858, access_token="access456", refresh_token="refresh456")

        # Корзины
        cart1 = Cart(
            telegram_id=1888565858,
            product_id=1,
            product_name="Product A",
            quantity=1,
            price=75.0,
            total_price=75.0,
            rating=5.0,
            latitude=40.0,
            longitude=70.0
        )
        cart2 = Cart(
            telegram_id=1888563858,
            product_id=2,
            product_name="Product B",
            quantity=1,
            price=75.0,
            total_price=75.0,
            rating=4.0,
            latitude=40.0,
            longitude=70.0
        )

        # Пользователи
        user1 = User(telegram_id=1888565858, full_name="John Doe", email="john@example.com", phone="123456789")
        user2 = User(telegram_id=1888563858, full_name="Jane Smith", email="jane@example.com", phone="987654321")

        # Заказы первого пользователя
        orders_user1 = []
        statuses = ["to‘langan", "bekor qilingan", "olib ketilgan", "to‘langan", "olib ketilgan",
                    "to‘langan", "bekor qilingan", "olib ketilgan", "to‘langan", "bekor qilingan",
                    "to‘langan", "olib ketilgan", "bekor qilingan", "to‘langan", "olib ketilgan",
                    "to‘langan", "bekor qilingan", "olib ketilgan", "to‘langan", "olib ketilgan"]
        for i, status in enumerate(statuses, start=1):
            orders_user1.append(Order(
                telegram_id=1888565858,
                items=[{"product_id": i, "product_name": f"Product {i}", "quantity": 1, "price": 10000 * i}],
                total_price=10000 * i,
                status=status,
                payment_status="paid",
                pickup_status="pending" if i % 2 == 0 else "picked_up",
                pickup_time="19:00 – 20:00",
                branch_name="Evos Chorsu",
                user_latitude=41.3200,
                user_longitude=69.2800,
            ))

        # Заказы второго пользователя
        orders_user2 = []
        statuses2 = ["to‘langan", "bekor qilingan", "olib ketilgan", "to‘langan", "bekor qilingan",
                     "olib ketilgan", "to‘langan", "bekor qilingan", "olib ketilgan", "to‘langan"]
        for i, status in enumerate(statuses2, start=1):
            orders_user2.append(Order(
                telegram_id=1888563858,
                items=[{"product_id": 20 + i, "product_name": f"Item {i}", "quantity": 1, "price": 15000 * i}],
                total_price=15000 * i,
                status=status,
                payment_status="paid",
                pickup_status="pending" if i % 2 == 0 else "picked_up",
                pickup_time="20:00 – 21:00",
                branch_name="Evos Yunusobod",
                user_latitude=41.3200,
                user_longitude=69.2800,
            ))

        session.add_all([
            user_lang1, user_lang2,
            token1, token2,
            cart1, cart2,
            user1, user2,
            *orders_user1, *orders_user2
        ])
        await session.commit()
        print("✅ Таблицы пересозданы и тестовые данные добавлены.")
