from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from models import User   # ⚠️ проверь, чтобы у тебя точно был models/User


class DataBaseSession(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            data["session"] = session

            tg_id = None
            tg_username = None

            # Поддерживаем и Message, и CallbackQuery
            if isinstance(event, Message):
                tg_id = event.from_user.id
                tg_username = event.from_user.username
            elif isinstance(event, CallbackQuery) and event.from_user:
                tg_id = event.from_user.id
                tg_username = event.from_user.username

            if tg_id:
                user = await session.get(User, tg_id)
                if not user:
                    # создаём нового пользователя
                    user = User(id=tg_id, username=tg_username)
                    session.add(user)
                    await session.commit()
                else:
                    # обновляем username при изменении
                    if tg_username and user.username != tg_username:
                        user.username = tg_username
                        await session.commit()

                data["user"] = user

            return await handler(event, data)
