from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, User

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select

from database.models import Users


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

            tg_user: Optional[User] = None
            if isinstance(event, Message):
                tg_user = event.from_user
            elif isinstance(event, CallbackQuery):
                tg_user = event.from_user

            user: Optional[Users] = None
            if tg_user is not None:
                result = await session.execute(select(Users).where(Users.user_id == tg_user.id))
                user = result.scalar_one_or_none()

                if user is None:
                    # Создаём пользователя с дефолтными настройками
                    user = Users(
                        user_id=tg_user.id,
                        username=tg_user.username,
                        first_name=tg_user.first_name,
                        last_name=tg_user.last_name,
                        news_subscribed=False,
                        events_subscribed=False,
                    )
                    session.add(user)
                    await session.commit()

            data["user"] = user
            return await handler(event, data)
