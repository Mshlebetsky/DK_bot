from aiogram import Router, types, F
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from database.models import Users, Events, UserEventTracking
from filter.filter import ChatTypeFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.orm_query import orm_get_user, orm_update_user_subscription, orm_add_user


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
def get_subscriptions_kb(user: Users):
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

    # Назад
    buttons.append([InlineKeyboardButton(text="🏠 В Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------- Сообщение (через кнопку) ----------
@notificate_router.message(F.text == "🔔 Подписки")
async def show_subscriptions(message: types.Message, session: AsyncSession):
    user = await get_or_create_user(session, message.from_user)
    text = "Здесь вы можете выбрать, какие уведомления вы будете получать, а также посмотреть отслеживаемые мероприятия"
    await message.answer(text, reply_markup=get_subscriptions_kb(user))


# ---------- Callback (из меню) ----------
@notificate_router.callback_query(F.data == 'notifications_')
async def show_subscriptions_(callback: CallbackQuery, session: AsyncSession):
    user = await get_or_create_user(session, callback.from_user)
    text = "Здесь вы можете выбрать, какие уведомления вы будете получать, а также посмотреть отслеживаемые мероприятия"
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

    for user_id in subscribers:
        try:
            try:
                await bot.send_photo(user_id, img, caption=text[:1024], parse_mode="HTML")
            except:
                await bot.send_message(user_id, text[:4096], parse_mode="HTML")
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")


# ---------- Напоминания о мероприятиях ----------
async def send_event_reminders(bot, session: AsyncSession):
    now = datetime.now().date()

    result = await session.execute(
        select(Events).where(Events.date.in_([now + timedelta(days=3), now + timedelta(days=1)]))
    )
    events = result.scalars().all()

    for event in events:
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
