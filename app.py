import os
import asyncio
import logging
import time

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from handlers.notification import send_event_reminders
from database.engine import Session, create_db, drop_db
from logic.scrap_control import scrap_everything
from middlewares.db import DataBaseSession
from filter.filter import get_admins_ids
from logic.cmd_list import private

# роутеры
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
import logging

# основной логгер
logger = logging.getLogger("bot")
logger.setLevel(logging.DEBUG)

# консоль (INFO и выше)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console_handler.setFormatter(console_format)

# файл (DEBUG и выше)
file_handler = logging.FileHandler("bot.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_format = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d | %(message)s"
)
file_handler.setFormatter(file_format)

# подключаем хендлеры
logger.addHandler(console_handler)
logger.addHandler(file_handler)


# ================= БОТ =================
load_dotenv()
bot = Bot(
    token=os.getenv("TOKEN"),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    timeout=60
)
bot.my_admins_list = get_admins_ids()

dp = Dispatcher()

# ================= РОУТЕРЫ =================
dp.include_router(menu2_router)
dp.include_router(admin_manage_router)
dp.include_router(news_router)
dp.include_router(notificate_router)
dp.include_router(user_private_router)
dp.include_router(admin_router)
dp.include_router(admin_events_router)
dp.include_router(admin_news_router)
dp.include_router(admin_studios_router)
dp.include_router(event_router)
dp.include_router(studios_router)
dp.include_router(servises_router)


# ================= APScheduler =================
def setup_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        send_reminders_job,
        trigger=CronTrigger(hour="9-21/1", minute=0),
        # trigger="interval",
        minutes=60,
        args=(bot,)
    )
    scheduler.add_job(
        scrap_everything,
        # trigger=CronTrigger(hour="9-21/2", minute=0),
        trigger="interval",
        minutes=60,
        args=(bot, True),  # True = уведомлять пользователей
    )


    scheduler.start()
    logger.info("✅ Планировщик запущен")


async def send_reminders_job(bot: Bot):
    try:
        session = Session()   # создаём сессию
        async with session:   # открываем контекст
            await send_event_reminders(bot, session)
        logger.info("🔔 Напоминания успешно отправлены")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминаний: {e}", exc_info=True)


# ================= STARTUP / SHUTDOWN =================
async def on_startup(bot: Bot):
    run_param = False
    if run_param:
        await drop_db()
    await create_db()
    logger.info("🚀 Бот запущен и БД инициализирована")


async def on_shutdown(bot: Bot):
    logger.info("🛑 Бот остановлен")


# ================= MAIN =================
async def main():
    while True:
        try:
            dp.startup.register(on_startup)
            dp.shutdown.register(on_shutdown)

            # Middleware с БД
            dp.update.middleware(DataBaseSession(session_pool=Session))

            await bot.delete_webhook(drop_pending_updates=True)
            # await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())

            setup_scheduler(bot)

            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except Exception as e:
            logger.error(f"Ошибка в polling: {e}", exc_info=True)
        else:
            break
        time.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
