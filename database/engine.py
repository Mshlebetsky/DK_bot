import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from database.models import Base

# создаём движок
engine = create_async_engine(
    os.getenv("DB_LITE"),
    echo=False,  # можно True для отладки SQL-запросов
    future=True
)

# фабрика для сессий
Session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# создание БД
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# удаление БД
async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
