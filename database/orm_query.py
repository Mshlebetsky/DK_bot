
from typing import Optional, Sequence
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import News, Events, Studios, Users


# -------------------- NEWS --------------------

async def orm_add_news(session: AsyncSession, data: dict) -> int:
    obj = News(
        name=data.get("name"),
        description=data.get("description"),
        img=data.get("img") or data.get("image"),
        is_shown=bool(data.get("is_shown", True))
    )
    session.add(obj)
    await session.flush()
    await session.commit()
    return obj.id

async def orm_get_all_news(session: AsyncSession) -> Sequence[News]:
    res = await session.execute(select(News).order_by(News.id.desc()))
    return res.scalars().all()

async def orm_get_news(session: AsyncSession, news_id: int) -> Optional[News]:
    res = await session.execute(select(News).where(News.id == news_id))
    return res.scalar_one_or_none()


async def orm_delete_news(session: AsyncSession, news_id: int):
    await session.execute(delete(News).where(News.id == news_id))
    await session.commit()


async def orm_get_news_by_name(session: AsyncSession, name: str):
    result = await session.execute(select(News).where(News.name == name))
    return result.scalars().first()

async def orm_update_news(session: AsyncSession, news_id: int, values: dict):
    await session.execute(
        update(News)
        .where(News.id == news_id)
        .values(**values)
    )
    await session.commit()

# -------------------- EVENTS --------------------


async def orm_get_all_events(session: AsyncSession) -> Sequence[Events]:
    res = await session.execute(select(Events).order_by(Events.date.desc(), Events.time.desc()))
    return res.scalars().all()

async def orm_get_event(session: AsyncSession, event_id: int) -> Optional[Events]:
    res = await session.execute(select(Events).where(Events.id == event_id))
    return res.scalar_one_or_none()


async def orm_add_event(session: AsyncSession, data: dict):
    obj = Events(**data)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)   # подтянем данные из БД (например id, created, updated)
    return obj

async def orm_get_events(session: AsyncSession, only_shown: bool = False):
    stmt = select(Events)
    if only_shown:
        stmt = stmt.where(Events.is_shown == True)
    result = await session.execute(stmt.order_by(Events.date))
    return result.scalars().all()

async def orm_update_event(session: AsyncSession, event_id: int, data: dict):
    await session.execute(update(Events).where(Events.id == event_id).values(**data))
    await session.commit()

async def orm_delete_event(session: AsyncSession, event_id: int):
    await session.execute(delete(Events).where(Events.id == event_id))
    await session.commit()

async def orm_get_event_by_name(session: AsyncSession, name: str):
    result = await session.execute(select(Events).where(Events.name == name))
    return result.scalars().first()

# -------------------- STUDIOS --------------------

async def orm_add_studio(session: AsyncSession, data: dict):
    new_studio = Studios(**{k: v for k, v in data.items() if k in Studios.__table__.c})
    session.add(new_studio)
    await session.commit()
    return new_studio.id


async def orm_update_studio(session: AsyncSession, studio_id: int, field: str, value):
    studio = await session.get(Studios, studio_id)
    if not studio:
        return False
    setattr(studio, field, value)
    await session.commit()
    return True


async def orm_delete_studio(session: AsyncSession, studio_id: int):
    studio = await session.get(Studios, studio_id)
    if studio:
        await session.delete(studio)
        await session.commit()
        return True
    return False


async def orm_get_all_studios(session: AsyncSession) -> Sequence[Studios]:
    res = await session.execute(select(Studios).order_by(Studios.id.desc()))
    return res.scalars().all()


async def orm_get_studio(session: AsyncSession, studio_id: int) -> Optional[Studios]:
    res = await session.execute(select(Studios).where(Studios.id == studio_id))
    return res.scalar_one_or_none()


async def orm_get_studios(session: AsyncSession):
    result = await session.execute(select(Studios))
    return result.scalars().all()


async def orm_get_studio_by_name(session: AsyncSession, name: str):
    query = select(Studios).where(Studios.name == name)
    result = await session.execute(query)
    return result.scalar_one_or_none()

# -------------------USERS---------------------------

# Получение юзера
async def orm_get_user(session: AsyncSession, user_id: int):
    return await session.get(Users, user_id)

# Обновление подписки
async def orm_update_user_subscription(session: AsyncSession, user_id: int, news: bool = None, events: bool = None):
    user = await session.get(Users, user_id)
    if not user:
        return
    if news is not None:
        user.news_subscribed = news
    if events is not None:
        user.events_subscribed = events
    await session.commit()

# Получение подписчиков
async def orm_get_subscribers(session: AsyncSession, type_: str):
    q = select(Users)
    if type_ == "news":
        q = q.where(Users.news_subscribed == True)
    elif type_ == "events":
        q = q.where(Users.events_subscribed == True)
    return (await session.execute(q)).scalars().all()

# Добавление пользователя в бд
async def orm_add_user(session: AsyncSession, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    user = await session.get(Users, user_id)
    if not user:
        user = Users(
            id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            news_subscribed=False,
            events_subscribed=False
        )
        session.add(user)
        await session.commit()
    return user

async def orm_get_user(session: AsyncSession, user_id: int):
    return await session.get(Users, user_id)