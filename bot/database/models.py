from datetime import datetime

from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, func, JSON
from .db_config import Base

class UserLang(Base):
    __tablename__ = "user_lang"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    lang = Column(String, default="uz")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserTokens(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Cart(Base):
    __tablename__ = "cart"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, index=True)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    rating = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    phone = Column(String)

    @property
    def formatted_registered_at(self):
        if self.registered_at:
            return self.registered_at.strftime("%d-%m-%Y %H:%M")
        return "-"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, index=True)
    items = Column(JSON, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String)  # статус заказа: "to‘langan", "bekor qilingan" и т.д.
    payment_status = Column(String, default="paid")  # "paid" или "pending"
    pickup_status = Column(String, default="to take")  # "to take" или "picked up"
    user_latitude = Column(Float)  # <-- добавляем
    user_longitude = Column(Float)
    pickup_time = Column(String)
    branch_name = Column(String)
    branch_latitude = Column(Float)
    branch_longitude = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def formatted_created_at(self):
        if self.created_at:
            return self.created_at.strftime("%d-%m-%Y %H:%M")
        return "-"

