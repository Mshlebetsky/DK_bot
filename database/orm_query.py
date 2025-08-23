
from typing import Optional, Sequence
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import News, Events, Studios

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

async def orm_update_news(session: AsyncSession, news_id: int, data: dict) -> bool:
    q = (
        update(News)
        .where(News.id == news_id)
        .values(
            name=data.get("name"),
            description=data.get("description"),
            img=data.get("img") or data.get("image"),
            is_shown=bool(data.get("is_shown", True)),
        )
        .execution_options(synchronize_session="fetch")
    )
    res = await session.execute(q)
    await session.commit()
    return res.rowcount > 0

async def orm_delete_news(session: AsyncSession, news_id: int) -> bool:
    res = await session.execute(delete(News).where(News.id == news_id))
    await session.commit()
    return res.rowcount > 0

# -------------------- EVENTS --------------------

async def orm_add_event(session: AsyncSession, data: dict) -> int:
    obj = Events(
        name=data.get("name"),
        is_free=bool(data.get("is_free", False)),
        link=data.get("link"),
        description=data.get("description"),
        date=data.get("date"),
        time=data.get("time"),
        age=data.get("age"),
        category=data.get("category"),
        qr_img=data.get("qr_img"),
        img=data.get("img"),
        is_shown=bool(data.get("is_shown", True)),
        announsed=bool(data.get("announsed", False)),
        price=data.get("price"),
        place=data.get("place"),
    )
    session.add(obj)
    await session.flush()
    await session.commit()
    return obj.id

async def orm_get_all_events(session: AsyncSession) -> Sequence[Events]:
    res = await session.execute(select(Events).order_by(Events.date.desc(), Events.time.desc()))
    return res.scalars().all()

async def orm_get_event(session: AsyncSession, event_id: int) -> Optional[Events]:
    res = await session.execute(select(Events).where(Events.id == event_id))
    return res.scalar_one_or_none()

async def orm_update_event(session: AsyncSession, event_id: int, data: dict) -> bool:
    q = (
        update(Events)
        .where(Events.id == event_id)
        .values(**{k: v for k, v in data.items() if k in Events.__table__.c})
        .execution_options(synchronize_session="fetch")
    )
    res = await session.execute(q)
    await session.commit()
    return res.rowcount > 0

async def orm_delete_event(session: AsyncSession, event_id: int) -> bool:
    res = await session.execute(delete(Events).where(Events.id == event_id))
    await session.commit()
    return res.rowcount > 0

# -------------------- STUDIOS --------------------

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

# ----------------EVENTS --------------------



# EVENTS
# async def orm_add_event(session: AsyncSession, data: dict):
#     event = Events(**data)
#     session.add(event)
#     await session.commit()
#

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

async def orm_get_event(session: AsyncSession, event_id: int):
    return await session.get(Events, event_id)

async def orm_update_event(session: AsyncSession, event_id: int, data: dict):
    await session.execute(update(Events).where(Events.id == event_id).values(**data))
    await session.commit()

async def orm_delete_event(session: AsyncSession, event_id: int):
    await session.execute(delete(Events).where(Events.id == event_id))
    await session.commit()


# ---------------- NEWS -------------------
async def orm_add_news(session: AsyncSession, data: dict):
    news = News(**data)
    session.add(news)
    await session.commit()

async def orm_get_news(session: AsyncSession):
    result = await session.execute(select(News))
    return result.scalars().all()

async def orm_get_news_item(session: AsyncSession, news_id: int):
    return await session.get(News, news_id)

async def orm_update_news(session: AsyncSession, news_id: int, data: dict):
    await session.execute(update(News).where(News.id == news_id).values(**data))
    await session.commit()

async def orm_delete_news(session: AsyncSession, news_id: int):
    await session.execute(delete(News).where(News.id == news_id))
    await session.commit()
