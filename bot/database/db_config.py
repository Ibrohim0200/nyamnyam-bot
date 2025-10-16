from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql+asyncpg://postgres:0200@localhost:5432/tg_bot"

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async_session = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()
