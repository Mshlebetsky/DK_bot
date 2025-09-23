import os
import logging
import subprocess
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from database.models import Base

# ================= ЛОГИРОВАНИЕ =================

logger = logging.getLogger(__name__)

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

from aiogram import types
async def drop_table_via_script(message: types.Message):
    """
    Вызывает скрипт drop_table.py через subprocess.
    """
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Использование: /drop_table <имя_таблицы>")
            return

        table_name = parts[1]

        # формируем команду для запуска скрипта
        cmd = [sys.executable, "database/drop_table.py", table_name]

        # выполняем синхронно, в отдельном процессе
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            await message.answer(result.stdout or f"⚠️ Таблица '{table_name}' удалена")
        else:
            await message.answer(result.stderr or "❌ Ошибка при удалении таблицы")

    except Exception as e:
        await message.answer(f"❌ Исключение: {e}")