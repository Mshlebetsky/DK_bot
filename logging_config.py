import logging
import sys
from pathlib import Path

# Папка для логов
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Файл для логов
LOG_FILE = LOG_DIR / "bot.log"

# Форматы логов
FILE_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
CONSOLE_FORMAT = "%(levelname)s: %(message)s"

import logging
import sys

def setup_logging(log_file: str = "logs/bot.log") -> None:
    """Настройка логирования: раздельно для консоли и файла."""
    # Уровень логов для нашего приложения
    log_level = logging.INFO

    # Основной логгер
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Хендлер для консоли (можно оставить INFO или DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    ))

    # Хендлер для файла (только INFO и выше)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    ))

    # Добавляем хендлеры
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # 🔹 Подавляем шум от сторонних библиотек
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    logger.info("✅ Логирование инициализировано")
