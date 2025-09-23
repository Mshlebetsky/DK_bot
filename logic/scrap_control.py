import asyncio
import logging
from datetime import datetime


from database import orm_query
from database.orm_query import (
    orm_update_event, orm_add_event,
    orm_update_news, orm_add_news,
    orm_update_studio, orm_add_studio, orm_get_studio_by_name, orm_delete_studio
)
from database.engine import Session
from logic.scrap_events import update_all_events
from logic.scrap_news import update_all_news
from logic.scrap_studios import update_all_studios

logger = logging.getLogger(__name__)


async def update_events(session, notify_users=False, bot=None):
    """Обновить все мероприятия и вернуть отчёт"""
    try:
        data, log_text = await asyncio.to_thread(update_all_events)
    except Exception as e:
        return {"status": "error", "msg": f"❌ Ошибка парсера событий: {e}"}

    updated, added = 0, 0
    new_items = []

    for name, values in data.items():
        try:
            event_date, description, age_limits, img, link, is_free = values
        except ValueError:
            logger.warning("⚠ Ошибка формата события: %s", name)
            continue

        event = await orm_query.orm_get_event_by_name(session, name)
        if event:
            if event.lock_changes == False:
                await orm_update_event(session, event.id, {
                    "date": datetime.strptime(event_date, "%Y-%m-%d %H:%M"),
                    "description": description,
                    "age_limits": age_limits,
                    "img": img,
                    "link": link,
                    "is_free": is_free
                })
                updated += 1
        else:
            await orm_add_event(session, {
                "name": name,
                "date": datetime.strptime(event_date, "%Y-%m-%d %H:%M"),
                "description": description,
                "age_limits": age_limits,
                "img": img,
                "link": link,
                "is_free": is_free
            })
            added += 1
            new_items.append((name, img, event_date, age_limits))

    return {
        "status": "ok",
        "type": "events",
        "updated": updated,
        "added": added,
        "new_items": new_items,
        "log": log_text
    }


async def update_news(session, notify_users=False, bot=None):
    """Обновить все новости"""
    try:
        data, log_text = await asyncio.to_thread(update_all_news)
    except Exception as e:
        return {"status": "error", "msg": f"❌ Ошибка парсера новостей: {e}"}

    updated, added = 0, 0
    new_items = []

    for name, values in data.items():
        try:
            description, img = values
        except ValueError:
            logger.warning("⚠ Ошибка формата новости: %s", name)
            continue

        news = await orm_query.orm_get_news_by_name(session, name)
        if news:
            if news.lock_changes == False:
                await orm_update_news(session, news.id, {"description": description, "img": img})
                updated += 1
        else:
            await orm_add_news(session, {"name": name, "description": description, "img": img})
            added += 1
            new_items.append((name, img))

    return {
        "status": "ok",
        "type": "news",
        "updated": updated,
        "added": added,
        "new_items": new_items,
        "log": log_text
    }


async def update_studios(session):
    """Обновить все студии"""
    try:
        data, log_text = await asyncio.to_thread(update_all_studios)
    except Exception as e:
        return {"status": "error", "msg": f"❌ Ошибка парсера студий: {e}"}

    updated, added = 0, 0
    for name, values in data.items():
        try:
            description, cost, second_cost, age, img, qr_img, teacher, category = values
        except ValueError:
            logger.warning("⚠ Ошибка формата студии: %s", name)
            continue

        studio = await orm_get_studio_by_name(session, name)
        if studio:
            if studio.lock_changes == False:
                logger.debug(f"Начато изменение студии {name}")
                try:
                    await orm_delete_studio(session, studio.id)
                except Exception as e:
                    logger.exception("Ошибка при массовом удалении студии id=%s: %s", studio.id, e)

                new_data = {
                    "name": name,
                    "description": description,
                    "teacher": teacher,
                    "cost": int(cost),
                    "second_cost": second_cost,
                    "age": age,
                    "category": category,
                    "qr_img": qr_img,
                    "img": img,
                }
                await orm_add_studio(session, new_data)
                updated += 1
                logger.debug("Обновлена студия %s", name)
                updated += 1
        else:
            new_data = {
                "name": name,
                "description": description,
                "teacher": teacher,
                "cost": int(cost),
                "second_cost": second_cost,
                "age": age,
                "category": category,
                "qr_img": qr_img,
                "img": img,
            }
            await orm_add_studio(session, new_data)
            added += 1

    return {
        "status": "ok",
        "type": "studios",
        "updated": updated,
        "added": added,
        "log": log_text
    }


from handlers.notification import notify_subscribers


async def scrap_everything(bot, notify_users: bool = True):
    """
    Последовательно обновляет события, новости и студии.
    notify_users=True → рассылает новые материалы подписчикам
    Возвращает сводный отчёт
    """
    logger.info("Начато плановое обновление")
    report = []
    async with Session() as session:
        # --- События ---
        res = await update_events(session, notify_users, bot)
        if res["status"] == "ok":
            report.append(f"🎭 События: обновлено {res['updated']}, добавлено {res['added']}")
            if notify_users:
                for name, img, event_date, age_limits in res["new_items"]:
                    text = f"📰 Обновление в афише!\n\n{name} | +{age_limits}\n{event_date}"
                    await notify_subscribers(bot, session, text, img, type_="events")
        else:
            report.append(res["msg"])

        # --- Новости ---
        res = await update_news(session, notify_users, bot)
        if res["status"] == "ok":
            report.append(f"📰 Новости: обновлено {res['updated']}, добавлено {res['added']}")
            if notify_users:
                for name, img in res["new_items"]:
                    text = f"📰 Обновление в новостях!\n\n{name}"
                    await notify_subscribers(bot, session, text, img, type_="news")
        else:
            report.append(res["msg"])

        # --- Студии ---
        res = await update_studios(session)
        if res["status"] == "ok":
            report.append(f"🎨 Студии: обновлено {res['updated']}, добавлено {res['added']}")
        else:
            report.append(res["msg"])

    return "\n".join(report)
