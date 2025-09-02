from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.future import select

from database.models import Users  # ⚠️ подключи свою модель User


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
            data['session'] = session

            user_id: Optional[int] = None
            if isinstance(event, Message):
                user_id = event.from_user.id
            elif isinstance(event, CallbackQuery):
                user_id = event.from_user.id

            user: Optional[Users] = None
            if user_id is not None:
                result = await session.execute(select(Users).where(Users.user_id == user_id))
                user = result.scalar_one_or_none()
                if user is None:
                    # Создаём нового пользователя с дефолтными настройками
                    user = Users(user_id=user_id, news_subscribed=False)
                    session.add(user)
                    await session.commit()

            data['user'] = user

            return await handler(event, data)
