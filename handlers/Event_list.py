import logging
from datetime import date, datetime
from typing import Sequence

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from database.models import Events, UserEventTracking
from database.orm_query import orm_get_event

# ================== ЛОГИРОВАНИЕ ==================

logger = logging.getLogger(__name__)

# ================== РОУТЕР ==================

event_router = Router()


EVENTS_PER_PAGE = 8


# ---------- Утилиты ----------

def capitalize_title_safe(s: str) -> str:
    """Делает первую букву заглавной, корректно обрабатывая кавычки и ёлочки."""
    if not s:
        return s
    if s[0] in {"«", "\""} and len(s) > 1:
        return f"{s[0]}{s[1:].capitalize()}"
    return s.capitalize()


async def safe_edit_message(message: Message, text: str, kb: InlineKeyboardMarkup | None = None) -> None:
    """
    Безопасное обновление сообщения:
    - если сообщение текстовое → edit_text
    - если сообщение фото/другое → delete + answer
    - защита от "message is not modified"
    """
    try:
        if message.content_type == "text":
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.delete()
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" in str(e):
            logger.debug("safe_edit_message: сообщение не изменилось")
        else:
            logger.warning(f"safe_edit_message error: {e}")


# ---------- Клавиатуры ----------

def get_events_keyboard(events: Sequence[Events], page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Формирует клавиатуру для списка событий."""
    keyboard = [
        [InlineKeyboardButton(
            text=f"🗓 {ev.date:%d.%m} | {capitalize_title_safe(ev.name[:30])} | {ev.age_limits}+",
            callback_data=f"event_card:{ev.id}:{page}"
        )]
        for ev in events
    ]

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⏮ Назад", callback_data=f"events_page:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="⏭ Далее", callback_data=f"events_page:{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton(text="🏠 В Главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_event_base_buttons(event: Events) -> list[list[InlineKeyboardButton]]:
    """Базовые кнопки для карточки события."""
    buttons = [[InlineKeyboardButton(text="🔗 Перейти на сайт", url="https://дк-яуза.рф/afisha/")]]
    if (
        event.link and isinstance(event.link, str) and event.link.startswith("http")
        and event.date >= datetime.now()
    ):
        buttons.append([InlineKeyboardButton(text="🎟 Приобрести билеты", url=event.link)])
    return buttons


def get_event_card_keyboard(event: Events, page: int, is_tracking: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для карточки события."""
    buttons = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"events_page:{page}")],
        [InlineKeyboardButton(text="ℹ Подробнее", callback_data=f"event_detail:{event.id}")],
    ]
    buttons.extend(get_event_base_buttons(event))
    track_text = "✅ Отслеживается" if is_tracking else "🔔 Отслеживать"
    track_action = "untrack_event" if is_tracking else "track_event"
    buttons.append([InlineKeyboardButton(text=track_text, callback_data=f"{track_action}:{event.id}:{page}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_event_detail_keyboard(event: Events, page: int, is_tracking: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для детального описания события."""
    buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data=f"event_card:{event.id}:{page}")]]
    buttons.extend(get_event_base_buttons(event))
    track_text = "✅ Отслеживается" if is_tracking else "🔔 Отслеживать"
    track_action = "untrack_event" if is_tracking else "track_event"
    buttons.append([InlineKeyboardButton(text=track_text, callback_data=f"{track_action}:{event.id}:{page}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------- Рендеры ----------

async def render_event_list(
    target: Message | CallbackQuery,
    session: AsyncSession,
    page: int = 1,
    edit: bool = False
) -> None:
    """Рендер списка событий с пагинацией."""
    logger.debug(f"User {target.from_user.id} открыл афишу")

    offset = (page - 1) * EVENTS_PER_PAGE
    events = (
        await session.execute(
            select(Events)
            .where(Events.date >= date.today())
            .order_by(Events.date.asc())
            .offset(offset)
            .limit(EVENTS_PER_PAGE)
        )
    ).scalars().all()

    total = (
        await session.execute(select(func.count(Events.id)).where(Events.date >= date.today()))
    ).scalar_one()

    total_pages = max((total + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE, 1)
    logger.debug("Найдено событий: %s, страниц: %s", total, total_pages)

    if not events:
        text = "❌ События не найдены"
        logger.info("События не найдены на странице %s", page)
        if isinstance(target, CallbackQuery):
            await safe_edit_message(target.message, text)
            await target.answer()
        else:
            await target.answer(text)
        return

    text = "📋 <b>Список ближайших событий:</b>\n\n"
    kb = get_events_keyboard(events, page, total_pages)

    if isinstance(target, CallbackQuery):
        if edit:
            await safe_edit_message(target.message, text, kb)
        else:
            await target.message.delete()
            await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


async def render_event_card(callback: CallbackQuery, session: AsyncSession, event_id: int, page: int) -> None:
    """Рендер карточки события."""
    logger.info(f"Пользователь {callback.from_user.id} просматривает событие {event_id}")

    event = await orm_get_event(session, event_id)
    if not event:
        logger.warning("Событие не найдено: %s", event_id)
        await callback.answer("Событие не найдено", show_alert=True)
        return

    tracking = await session.execute(
        select(UserEventTracking).where(
            UserEventTracking.user_id == callback.from_user.id,
            UserEventTracking.event_id == event_id
        )
    )
    is_tracking = tracking.scalars().first() is not None

    desc = event.description or "Нет описания"
    short_desc = desc[:350] + (
        "<i>… \n\nнажмите на <b>\"Подробнее\"</b> чтобы посмотреть больше</i>"
        if len(desc) > 350 else ""
    )
    date_line = f"🗓 {event.date:%d.%m.%Y}\n\n" if getattr(event, "date", None) else ""
    text = f"<b>{event.name} | {event.age_limits}+ </b>\n\n{date_line}{short_desc}"

    kb = get_event_card_keyboard(event, page, is_tracking=is_tracking)

    try:
        await callback.message.delete()
    except Exception:
        pass

    try:
        await callback.message.answer_photo(
            event.img,
            caption=text[:1024],
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning("Ошибка при отправке фото события %s: %s", event_id, e)
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

    await callback.answer()


async def render_event_detail(callback: CallbackQuery, session: AsyncSession, event_id: int, page: int) -> None:
    """Рендер детального описания события."""
    logger.debug("Открытие детального описания события: event_id=%s, page=%s", event_id, page)

    event = await orm_get_event(session, event_id)
    if not event:
        logger.warning("Событие не найдено: %s", event_id)
        await callback.answer("Событие не найдено", show_alert=True)
        return

    text = (
        f"<b>{event.name} | {event.age_limits}+</b>\n\n"
        f"🗓 {event.date:%d.%m.%Y %H:%M}\n\n"
        f"{event.description or 'Нет описания'}"
    )

    tracking = await session.execute(
        select(UserEventTracking).where(
            UserEventTracking.user_id == callback.from_user.id,
            UserEventTracking.event_id == event_id
        )
    )
    is_tracking = tracking.scalars().first() is not None

    kb = get_event_detail_keyboard(event, page, is_tracking=is_tracking)

    await safe_edit_message(callback.message, text, kb)
    await callback.answer()


# ---------- Хендлеры ----------

@event_router.message(Command("events"))
async def cmd_event_list(message: Message, session: AsyncSession) -> None:
    await render_event_list(message, session, page=1)


@event_router.callback_query(F.data == "list_events")
async def list_events_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    await render_event_list(callback, session, page=1)


@event_router.callback_query(F.data.startswith("events_page:"))
async def events_page_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    page = int(callback.data.split(":")[1])
    await render_event_list(callback, session, page, edit=True)


@event_router.callback_query(F.data.startswith("event_card:"))
async def event_card_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    _, event_id, page = callback.data.split(":")
    await render_event_card(callback, session, int(event_id), int(page))


@event_router.callback_query(F.data.startswith("event_detail:"))
async def event_detail_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    _, event_id = callback.data.split(":")
    await render_event_detail(callback, session, int(event_id), page=1)


@event_router.callback_query(F.data.startswith("track_event:"))
async def track_event_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    _, event_id, page = callback.data.split(":")
    user_id = callback.from_user.id

    existing = await session.execute(
        select(UserEventTracking).where(
            UserEventTracking.user_id == user_id,
            UserEventTracking.event_id == int(event_id)
        )
    )
    if not existing.scalars().first():
        session.add(UserEventTracking(user_id=user_id, event_id=int(event_id)))
        await session.commit()
        logger.info("Пользователь %s подписался на событие %s", user_id, event_id)

    await callback.answer("✅ Вы подписались на напоминания")
    await render_event_detail(callback, session, int(event_id), int(page))


@event_router.callback_query(F.data.startswith("untrack_event:"))
async def untrack_event_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    _, event_id, page = callback.data.split(":")
    user_id = callback.from_user.id

    await session.execute(
        delete(UserEventTracking).where(
            UserEventTracking.user_id == user_id,
            UserEventTracking.event_id == int(event_id)
        )
    )
    await session.commit()
    logger.info("Пользователь %s отписался от события %s", user_id, event_id)

    await callback.answer("❌ Напоминание снято")
    await render_event_detail(callback, session, int(event_id), int(page))