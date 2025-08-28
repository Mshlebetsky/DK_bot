from aiogram import Router, types, F
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import Users

from datetime import datetime, timedelta
from database.models import Events, UserEventTracking
from filter.filter import ChatTypeFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.orm_query import orm_get_user, orm_update_user_subscription, orm_get_subscribers

notificate_router = Router()
notificate_router.message.filter(ChatTypeFilter(["private"]))


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

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@notificate_router.message(F.text == "🔔 Подписки")
async def show_subscriptions(message: types.Message, session: AsyncSession):
    user = await orm_get_user(session, message.from_user.id)
    text = f"Здесь вы можете выбрать, какие уведомления вы будете получать, а также посмотреть отслеживаемые мероприятия"
    await message.answer("Выберите подписки:", reply_markup=get_subscriptions_kb(user))


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

async def notify_subscribers(bot, session, text: str, img: str | None = None, type_: str = "news"):
    """
    Рассылает уведомления подписчикам о новостях или событиях.
    :param bot: экземпляр aiogram.Bot
    :param session: AsyncSession
    :param text: текст уведомления
    :param img: (опционально) ссылка на фото
    :param type_: "news" или "event"
    """
    if type_ == "news":
        filter_field = Users.news_subscribed
    else:
        filter_field = Users.events_subscribed

    result = await session.execute(select(Users.user_id).where(filter_field == True))
    subscribers = result.scalars().all()

    for user_id in subscribers:
        try:
            if img:
                await bot.send_photo(user_id, img, caption=text[:1024], parse_mode="HTML")
            else:
                await bot.send_message(user_id, text[:4096], parse_mode="HTML")
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

async def send_event_reminders(bot, session):
    now = datetime.now().date()

    # выбираем события, которые будут через 3 дня или через 1 день
    result = await session.execute(
        select(Events)
        .where(Events.date.in_([now + timedelta(days=3), now + timedelta(days=1)]))
    )
    events = result.scalars().all()

    for event in events:
        # находим всех пользователей, кто отслеживает это событие
        tracking_users = await session.execute(
            select(UserEventTracking.user_id).where(UserEventTracking.event_id == event.id)
        )
        user_ids = tracking_users.scalars().all()

        text = (
            f"🔔 Напоминание!\n\n"
            f"Через {'3 дня' if event.date.date() == now + timedelta(days=3) else '1 день'} состоится мероприятие:\n\n"
            f"<b>{event.name}</b>\n"
            f"🗓 {event.date:%d.%m.%Y}\n\n"
            f"{event.description[:200]}..."
        )

        for user_id in user_ids:
            try:
                if event.img:
                    await bot.send_photo(user_id, event.img, caption=text, parse_mode="HTML")
                else:
                    await bot.send_message(user_id, text, parse_mode="HTML")
            except Exception as e:
                print(f"Не удалось отправить напоминание {user_id}: {e}")