import os
import asyncio
from aiogram import Bot, Dispatcher, types

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())

from middlewares.db import DataBaseSession

from database.engine import create_db, drob_db, session_maker

from filter.filter import check_message, get_admins_ids

from handlers.user_private import user_private_router
from handlers.user_studios import user_studios_router
from handlers.admin_panel import user_router, admin_router
from handlers.admin_news import admin_news_router
# from handlers.admin_news import95 admin_router
from handlers.admin_events import admin_events_router
from handlers.user_events import user_events_router
from handlers.admin_studios import admin_studios_router

from logic.cmd_list import private


bot = Bot(token=os.getenv('TOKEN'))
bot.my_admins_list = get_admins_ids()


dp = Dispatcher()

dp.include_router(user_private_router)
dp.include_router(user_router)
dp.include_router(admin_router)
dp.include_router(user_events_router)
dp.include_router(admin_events_router)
dp.include_router(admin_news_router)
dp.include_router(admin_studios_router)
dp.include_router(user_studios_router)


async def on_startup(bot):
    run_param = False
    if run_param:
        await drob_db()
    await create_db()

async def on_shutdown(bot):
    print('sosi bot umer')
async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.update.middleware(DataBaseSession(session_pool=session_maker))

    await bot.delete_webhook(drop_pending_updates=True)

    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

asyncio.run(main())