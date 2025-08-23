import os
from dotenv import find_dotenv, load_dotenv

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
async def check_message(message: types.Message) -> bool:
    return str(message.from_user.id) in admins_list
def get_admins_ids() -> list[str]:
    return admins_list
# print(admins_list)