from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models import Users   # ⚠️ Подключи свою модель User


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

            # --- Получаем ID пользователя (если это апдейт от юзера) ---
            user_id = getattr(getattr(event, "from_user", None), "id", None)

            if user_id:
                user = await session.get(Users, user_id)
                if user is None:
                    # Создаём нового пользователя
                    user = Users(id=user_id)
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)

                data["user"] = user

            return await handler(event, data)
