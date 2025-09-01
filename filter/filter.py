import os
from dotenv import find_dotenv, load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import Admin

load_dotenv(find_dotenv())

from aiogram.filters import Filter
from aiogram import Bot, types


class ChatTypeFilter(Filter):
    def __init__(self, chat_types: list[str]) -> None:
        self.chat_types = chat_types

    async def __call__(self, message: types.Message) -> bool:
        return message.chat.type in self.chat_types


class IsAdmin(Filter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        return str(message.from_user.id) in bot.my_admins_list
        # return message.from_user.id in [435946390]


admins_list = os.getenv("ADMINS_LIST").replace(' ','').split(',')
def check_message(message: types.Message) -> bool:
    admins_list = os.getenv("ADMINS_LIST").replace(' ', '').split(',')
    return str(message.from_user.id) in admins_list
def get_admins_ids() -> list[str]:
    return os.getenv("ADMINS_LIST").replace(' ', '').split(',')
def check_user(user :types.User) -> bool:
    admins_list = os.getenv("ADMINS_LIST").replace(' ', '').split(',')
    return str(user.id) in admins_list

class IsSuperAdmin(Filter):
    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        return str(message.from_user.id) in bot.my_admins_list


class IsEditor(Filter):
    async def __call__(self, message: types.Message, session: AsyncSession) -> bool:
        # проверяем в БД
        result = await session.execute(
            select(Admin).where(Admin.user_id == message.from_user.id, Admin.role == "editor")
        )
        return result.scalar_one_or_none() is not None