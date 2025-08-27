from aiogram import Router, types, F
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram import Bot
from database.models import Users

from filter.filter import ChatTypeFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.orm_query import orm_get_user, orm_update_user_subscription, orm_get_subscribers

notificate_router = Router()
notificate_router.message.filter(ChatTypeFilter(["private"]))


def get_subscriptions_kb(user):
    buttons = []

    # Новости
    if user.news_subscribed:
        buttons.append([InlineKeyboardButton(text="❌ Отписаться от новостей", callback_data="unsub_news")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ Подписаться на новости", callback_data="sub_news")])

    # Мероприятия
    if user.events_subscribed:
        buttons.append([InlineKeyboardButton(text="❌ Отписаться от мероприятий", callback_data="unsub_events")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ Подписаться на мероприятия", callback_data="sub_events")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@notificate_router.message(F.text == "🔔 Подписки")
async def show_subscriptions(message: types.Message, session: AsyncSession):
    user = await orm_get_user(session, message.from_user.id)
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

async def notify_subscribers(bot: Bot, session: AsyncSession, text: str, img: str = None):
    # достаём всех подписанных пользователей
    result = await session.execute(
        select(Users.id).where(Users.news_subscribed == True)
    )
    subscribers = [row[0] for row in result.fetchall()]

    if not subscribers:
        return  # никто не подписан — выходим

    for user_id in subscribers:
        try:
            if img:
                await bot.send_photo(user_id, img, caption=text, parse_mode="HTML")
            else:
                await bot.send_message(user_id, text, parse_mode="HTML")
        except Exception as e:
            # например, пользователь заблокировал бота
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")