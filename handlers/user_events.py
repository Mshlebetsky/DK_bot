from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import orm_get_events, orm_get_event
from logic.helper import send_entity_card, send_entity_full


from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import or_f, Command
from handlers.user_private import Default_Keyboard
import re

user_events_router = Router()


EVENTS_PER_PAGE = 8


def get_events_kb(events, page: int, total_pages: int):
    buttons = []
    for ev in events:
        buttons.append([InlineKeyboardButton(text=ev.name, callback_data=f"event_detail:{ev.id}")])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"events_page:{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="➡️ Далее", callback_data=f"events_page:{page+1}"))

    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@user_events_router.message(or_f(Command('events'),(F.text == "📆Афиша мероприятий")))
async def show_events(message: types.Message, session: AsyncSession):
    events = await orm_get_events(session, only_shown=True)
    # events = await orm_get_events(session)

    if not events:
        await message.answer("❌ Мероприятий пока нет")
        return

    total_pages = (len(events) - 1) // EVENTS_PER_PAGE + 1
    page = 1
    start = (page - 1) * EVENTS_PER_PAGE
    end = start + EVENTS_PER_PAGE
    kb = get_events_kb(events[start:end], page, total_pages)

    await message.answer("📌 <b>Список мероприятий:</b>", parse_mode="HTML", reply_markup=kb)


@user_events_router.callback_query(F.data.startswith("events_page:"))
async def paginate_events(callback: types.CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    events = await orm_get_events(session, only_shown=True)

    total_pages = (len(events) - 1) // EVENTS_PER_PAGE + 1
    start = (page - 1) * EVENTS_PER_PAGE
    end = start + EVENTS_PER_PAGE
    kb = get_events_kb(events[start:end], page, total_pages)

    await callback.message.edit_text("📌 <b>Список мероприятий:</b>", parse_mode="HTML", reply_markup=kb)

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@user_events_router.callback_query(F.data.startswith("event_detail:"))
async def event_detail(callback: types.CallbackQuery, session: AsyncSession):
    event_id = int(callback.data.split(":")[1])
    event = await orm_get_event(session, event_id)

    if not event:
        await callback.answer("❌ Мероприятие не найдено", show_alert=True)
        return

    await send_entity_card(
        callback,
        event,
        back_cb="events_list:1",   # назад к списку
        detail_cb=f"event_full:{event.id}"
    )


@user_events_router.callback_query(F.data.startswith("event_full:"))
async def event_full(callback: types.CallbackQuery, session: AsyncSession):
    event_id = int(callback.data.split(":")[1])
    event = await orm_get_event(session, event_id)
    if event:
        await send_entity_full(callback, event, back_cb="events_list:1")
