import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from database.models import Base

# ================= ЛОГИРОВАНИЕ =================
logger = logging.getLogger("bot.database")

# ================= ДВИЖОК =================
DB_URL = os.getenv("DB_LITE")
if not DB_URL:
    logger.critical("❌ Не задана переменная окружения DB_LITE")
    raise RuntimeError("Отсутствует DB_LITE в .env")

# Создаём асинхронный движок SQLAlchemy
engine = create_async_engine(
    DB_URL,
    echo=False,   # echo=True — для отладки SQL-запросов
    future=True
)

# Фабрика асинхронных сессий
Session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# ================= УПРАВЛЕНИЕ БД =================
async def create_db() -> None:
    """Создаёт все таблицы в базе данных."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("📦 Таблицы успешно созданы (или уже существуют)")
    except Exception as e:
        logger.error(f"Ошибка при создании БД: {e}", exc_info=True)
        raise


async def drop_db() -> None:
    """Удаляет все таблицы из базы данных."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("⚠️ Все таблицы удалены")
    except Exception as e:
        logger.error(f"Ошибка при удалении БД: {e}", exc_info=True)
        raise