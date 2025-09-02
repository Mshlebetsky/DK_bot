import asyncio
import os
from aiogram import Bot, types
from dotenv import load_dotenv
from logic.cmd_list import private

load_dotenv()

async def main():
    bot = Bot(token=os.getenv("TOKEN"))
    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
    print("✅ Команды успешно установлены")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
