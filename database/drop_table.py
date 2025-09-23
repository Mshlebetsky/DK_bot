# drop_table.py
import sys
import os
import logging
from sqlalchemy import create_engine, MetaData, Table
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
DB_URL = os.getenv("DB_LITE")
if not DB_URL:
    raise RuntimeError("Отсутствует DB_LITE в .env")

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    if len(sys.argv) != 2:
        logger.error("Использование: python drop_table.py <имя_таблицы>")
        sys.exit(1)

    table_name = sys.argv[1].lower()  # sqlite чувствителен к регистру

    # создаём синхронный движок
    sync_engine = create_engine(DB_URL.replace("+aiosqlite", ""), echo=False)

    metadata = MetaData()
    metadata.reflect(bind=sync_engine)

    if table_name not in metadata.tables:
        logger.warning(f"⚠️ Таблица '{table_name}' не найдена")
        sys.exit(0)

    table = metadata.tables[table_name]
    table.drop(bind=sync_engine)
    logger.info(f"⚠️ Таблица '{table_name}' удалена")

if __name__ == "__main__":
    main()
