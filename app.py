import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from handlers.notification import send_event_reminders
from database.engine import Session, create_db, drop_db
from logic.scrap_control import scrap_everything
from middlewares.db import DataBaseSession
from filter.filter import get_admins_ids
from logic.cmd_list import private

# Роутеры
from handlers.user_private import user_private_router
from handlers.admin_panel import admin_router, admin_manage_router
from handlers.admin_news import admin_news_router
from handlers.admin_events import admin_events_router
from handlers.admin_studios import admin_studios_router
from handlers.Studio_list import studios_router
from handlers.Event_list import event_router
from handlers.News_list import news_router
from handlers.notification import notificate_router
from handlers.Serviсes import servises_router
from handlers.menu2 import menu2_router

# ================= ЛОГИРОВАНИЕ =================
logger = logging.getLogger("bot")
logger.setLevel(logging.DEBUG)

# Консоль (INFO и выше)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console_handler.setFormatter(console_format)

# Файл (DEBUG и выше)
file_handler = logging.FileHandler("bot.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_format = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d | %(message)s"
)
file_handler.setFormatter(file_format)

# Подключаем хендлеры логирования
logger.addHandler(console_handler)
logger.addHandler(file_handler)


# ================= ИНИЦИАЛИЗАЦИЯ БОТА =================
load_dotenv()
token = os.getenv("TOKEN")

if not token:
    logger.critical("❌ Не найден токен в .env (TOKEN)")
    raise RuntimeError("Отсутствует TOKEN в .env")

bot = Bot(
    token=token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    timeout=60
)

# Список админов из БД
bot.my_admins_list = get_admins_ids()

# Диспетчер
dp = Dispatcher()


# ================= РОУТЕРЫ =================
def setup_routers(dp: Dispatcher) -> None:
    """Регистрация всех роутеров."""
    routers = [
        menu2_router,
        admin_manage_router,
        news_router,
        notificate_router,
        user_private_router,
        admin_router,
        admin_events_router,
        admin_news_router,
        admin_studios_router,
        event_router,
        studios_router,
        servises_router,
    ]
    for router in routers:
        dp.include_router(router)
    logger.info("✅ Все роутеры подключены")


# ================= APScheduler =================
def setup_scheduler(bot: Bot) -> None:
    """Настройка планировщика задач."""
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Оповещения — только в 9:00
    scheduler.add_job(
        send_reminders_job,
        trigger=CronTrigger(hour=9, minute=0),
        args=(bot,),
    )

    # Обновления — в 9:00 и 17:00
    scheduler.add_job(
        scrap_everything,
        trigger=CronTrigger(hour=9, minute=0),
        args=(bot, True),
    )
    scheduler.add_job(
        scrap_everything,
        trigger=CronTrigger(hour=17, minute=0),
        args=(bot, True),
    )

    scheduler.start()
    logger.info("✅ Планировщик запущен")


async def send_reminders_job(bot: Bot):
    """Фоновая задача для отправки напоминаний."""
    try:
        session = Session()
        async with session:
            await send_event_reminders(bot, session)
        logger.info("🔔 Напоминания успешно отправлены")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминаний: {e}", exc_info=True)


# ================= STARTUP / SHUTDOWN =================
async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    run_param = False
    if run_param:
        await drop_db()
    await create_db()
    logger.info("🚀 Бот запущен и БД инициализирована")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота."""
    logger.info("🛑 Бот остановлен")


# ================= MAIN =================
async def main():
    """Главная точка входа."""
    while True:
        try:
            # Регистрируем события старта и остановки
            dp.startup.register(on_startup)
            dp.shutdown.register(on_shutdown)

            # Middleware для БД
            dp.update.middleware(DataBaseSession(session_pool=Session))

            # Удаляем webhook (на случай перезапуска)
            await bot.delete_webhook(drop_pending_updates=True)

            # Подключаем роутеры
            setup_routers(dp)

            # Настройка планировщика
            setup_scheduler(bot)

            # Запуск polling
            logger.info("▶️ Запуск long polling")
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except Exception as e:
            logger.error(f"Ошибка в polling: {e}", exc_info=True)
        else:
            break
        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен вручную (KeyboardInterrupt)")