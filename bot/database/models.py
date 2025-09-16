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
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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