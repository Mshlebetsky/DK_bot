from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from sqlalchemy import select
import logging

from database.models import Users, Events, UserEventTracking
from filter.filter import ChatTypeFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.orm_query import orm_get_user, orm_update_user_subscription, orm_add_user


logger = logging.getLogger("bot.handlers.reminders")


notificate_router = Router()
notificate_router.message.filter(ChatTypeFilter(["private"]))


# ---------- Утилита ----------
async def get_or_create_user(session: AsyncSession, tg_user: types.User):
    """Получить пользователя из БД или создать нового"""
    user = await orm_get_user(session, tg_user.id)
    if not user:
        user = await orm_add_user(
            session,
            user_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
        )
    return user


# ---------- Клавиатура подписок ----------
def get_subscriptions_kb(user):
    buttons = []

    # Новости
    if user.news_subscribed:
        buttons.append([InlineKeyboardButton(text="✅ Вы подписаны на новости", callback_data="unsub_news")])
    else:
        buttons.append([InlineKeyboardButton(text="❌ Вы не подписаны на новости", callback_data="sub_news")])

    # Мероприятия
    if user.events_subscribed:
        buttons.append([InlineKeyboardButton(text="✅ Вы подписаны на афишу", callback_data="unsub_events")])
    else:
        buttons.append([InlineKeyboardButton(text="❌ Вы не подписаны на афишу", callback_data="sub_events")])

    buttons.append([InlineKeyboardButton(text="🏠 В Главное меню", callback_data='main_menu')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def build_subscriptions_text(session, user_id: int) -> str:
    """
    Формирует текст для вкладки подписок: подписки + отслеживаемые мероприятия (только будущие).
    """
    # Подписки пользователя
    result = await session.execute(
        select(UserEventTracking.event_id).where(UserEventTracking.user_id == user_id)
    )
    event_ids = result.scalars().all()

    text = "Здесь вы можете управлять подписками.\n\n"

    if event_ids:
        now = datetime.now()
        events = await session.execute(
            select(Events).where(
                Events.id.in_(event_ids),
                Events.date >= now  # показываем только актуальные
            )
        )
        events = events.scalars().all()

        if events:
            text += "📌 Вы отслеживаете следующие мероприятия:\n"
            for ev in events:
                text += f" • <b>{ev.name}</b> — {ev.date:%d.%m.%Y %H:%M}\n"
        else:
            text += "📌 У вас нет актуальных отслеживаемых мероприятий.\n"
    else:
        text += "📌 Вы пока не отслеживаете мероприятия.\n"

    return text


# ---------- Сообщение (через кнопку) ----------
@notificate_router.message(Command('notifications'))
async def show_subscriptions(message: types.Message, session: AsyncSession, user: Users):
    text = await build_subscriptions_text(session, user.user_id)
    await message.answer(text, reply_markup=get_subscriptions_kb(user))



@notificate_router.callback_query(F.data == 'notifications_')
async def show_subscriptions_(callback: CallbackQuery, session: AsyncSession):
    user = await orm_get_user(session, callback.from_user.id)
    text = await build_subscriptions_text(session, callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=get_subscriptions_kb(user))


# ---------- Подписка / Отписка ----------
@notificate_router.callback_query(F.data.in_(["sub_news", "unsub_news", "sub_events", "unsub_events"]))
async def toggle_subscription(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id

    if callback.data == "sub_news":
        await orm_update_user_subscription(session, user_id, news=True)
        text = "✅ Подписка на новости оформлена!"
    elif callback.data == "unsub_news":
        await orm_update_user_subscription(session, user_id, news=False)
        text = "❌ Подписка на новости отменена."
    elif callback.data == "sub_events":
        await orm_update_user_subscription(session, user_id, events=True)
        text = "✅ Подписка на мероприятия оформлена!"
    else:
        await orm_update_user_subscription(session, user_id, events=False)
        text = "❌ Подписка на мероприятия отменена."

    user = await orm_get_user(session, user_id)
    await callback.message.edit_reply_markup(reply_markup=get_subscriptions_kb(user))
    await callback.answer(text)


# ---------- Рассылка новостей и событий ----------
async def notify_subscribers(bot, session: AsyncSession, text: str, img: str | None = None, type_: str = "news"):
    if type_ == "news":
        filter_field = Users.news_subscribed
    else:
        filter_field = Users.events_subscribed

    result = await session.execute(select(Users.user_id).where(filter_field == True))
    subscribers = result.scalars().all()
    kb_news = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗞Новости", callback_data="list_news")]])
    kb_events = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📆Афиша мероприятий", callback_data="list_events")]])
    for user_id in subscribers:
        try:
            try:
                await bot.send_photo(user_id, img, caption=text[:1024], parse_mode="HTML", reply_markup=kb_news if type_ == 'news' else kb_events)
            except:
                await bot.send_message(user_id, text[:4096], parse_mode="HTML")
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")


# ---------- Напоминания о мероприятиях ----------
async def send_event_reminders(bot, session):
    now = datetime.now().date()
    two_weeks = now + timedelta(days=2)

    # выбираем события на ближайшие 2 недели
    result = await session.execute(
        select(Events).where(Events.date.between(now, two_weeks))
    )
    events = result.scalars().all()

    if not events:
        logger.info("Нет событий в ближайшие 2 недели")
        return

    for event in events:
        # находим пользователей, отслеживающих событие
        tracking_users = await session.execute(
            select(UserEventTracking.user_id).where(UserEventTracking.event_id == event.id)
        )
        user_ids = tracking_users.scalars().all()

        if not user_ids:
            continue

        # считаем разницу в днях
        days_left = (event.date.date() - now).days
        if days_left < 0:
            continue
        elif days_left == 0:
            text = (
                f"🔔 Напоминание!\n\n"
                f"Уже Сегодня состоится мероприятие:\n\n"
                f"<b>{event.name}</b>\n"
                f"🗓 {event.date:%d.%m.%Y %H:%M}\n\n"
                f"{(event.description or '')[:200]}..."
            )
        else:
            text = (
                f"🔔 Напоминание!\n\n"
                f"Через {days_left} {'день' if days_left == 1 else 'дней'} состоится мероприятие:\n\n"
                f"<b>{event.name}</b>\n"
                f"🗓 {event.date:%d.%m.%Y %H:%M}\n\n"
                f"{(event.description or '')[:200]}..."
            )

        # рассылаем уведомления
        for user_id in user_ids:
            try:
                if event.img:
                    try:
                        await bot.send_photo(user_id, event.img, caption=text, parse_mode="HTML",reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[[InlineKeyboardButton(text="📆Афиша мероприятий", callback_data="list_events")]]))
                    except Exception:
                        await bot.send_message(user_id, text, parse_mode="HTML")
                else:
                    await bot.send_message(user_id, text, parse_mode="HTML")

                logger.info(f"Напоминание отправлено пользователю {user_id} о событии {event.id}")
            except Exception as e:
                logger.warning(f"❌ Не удалось отправить {user_id}: {e}")


logger = logging.getLogger("bot.broadcast")


async def notify_all_users(bot, session, text: str, img: str | None = None):
    """
    Отправка уведомления всем пользователям из таблицы Users
    """
    # достаём всех пользователей
    result = await session.execute(select(Users.user_id))
    user_ids = result.scalars().all()

    logger.info(f"📢 Рассылка по {len(user_ids)} пользователям")

    kb_main = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )

    for user_id in user_ids:
        try:
            if img:
                try:
                    await bot.send_photo(
                        user_id,
                        img,
                        caption=text[:1024],
                        parse_mode="HTML",
                        reply_markup=kb_main,
                    )
                except Exception:
                    await bot.send_message(
                        user_id,
                        text[:4096],
                        parse_mode="HTML",
                        reply_markup=kb_main,
                    )
            else:
                await bot.send_message(
                    user_id,
                    text[:4096],
                    parse_mode="HTML",
                    reply_markup=kb_main,
                )
        except Exception as e:
            logger.warning(f"❌ Не удалось отправить сообщение {user_id}: {e}")