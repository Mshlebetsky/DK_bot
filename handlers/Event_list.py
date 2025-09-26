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

def get_category_menu() -> InlineKeyboardMarkup:
    """Меню выбора: бесплатные или платные события"""
    category_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Бесплатные", callback_data="events_free:1")],
        [InlineKeyboardButton(text="💳 Платные", callback_data="events_paid:1")],
        [InlineKeyboardButton(text="🏠 В Главное меню", callback_data="main_menu")]
    ])
    return category_kb


def get_events_keyboard(events: Sequence[Events], page: int, total_pages: int, is_free: bool) -> InlineKeyboardMarkup:
    """Формирует клавиатуру для списка событий."""
    keyboard = [
        [InlineKeyboardButton(
            text=f"🗓 {ev.date:%d.%m} | {capitalize_title_safe(ev.name[:30]) if ev.title == '' else ev.title[:30]} | {ev.age_limits}+",
            callback_data=f"event_card:{ev.id}:{page}:{int(is_free)}"
        )]
        for ev in events
    ]

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⏮ Назад", callback_data=f"events_page:{page-1}:{int(is_free)}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="⏭ Далее", callback_data=f"events_page:{page+1}:{int(is_free)}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton(text="⬅ К категориям", callback_data="events")])
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


def get_event_card_keyboard(event: Events, page: int, is_free: bool, is_tracking: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для карточки события."""
    buttons = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"events_page:{page}:{int(is_free)}")],
        [InlineKeyboardButton(text="ℹ Подробнее", callback_data=f"event_detail:{event.id}:{page}:{int(is_free)}")],
    ]
    buttons.extend(get_event_base_buttons(event))
    track_text = "✅ Отслеживается" if is_tracking else "🔔 Отслеживать"
    track_action = "untrack_event" if is_tracking else "track_event"
    buttons.append([InlineKeyboardButton(text=track_text, callback_data=f"{track_action}:{event.id}:{page}:{int(is_free)}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_event_detail_keyboard(event: Events, page: int, is_free: bool, is_tracking: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для детального описания события."""
    buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data=f"event_card:{event.id}:{page}:{int(is_free)}")]]
    buttons.extend(get_event_base_buttons(event))
    track_text = "✅ Отслеживается" if is_tracking else "🔔 Отслеживать"
    track_action = "untrack_event" if is_tracking else "track_event"
    buttons.append([InlineKeyboardButton(text=track_text, callback_data=f"{track_action}:{event.id}:{page}:{int(is_free)}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------- Рендеры ----------

async def render_category_menu(target: Message | CallbackQuery):
    try:
        await target.message.edit_text('Выберите тип мероприятий:', reply_markup=get_category_menu())
    except:
        await target.answer('Выберите тип мероприятий:', reply_markup=get_category_menu())


async def render_event_list(
    target: Message | CallbackQuery,
    session: AsyncSession,
    is_free: bool,
    page: int = 1,
    edit: bool = False
) -> None:
    """Рендер списка событий с учётом фильтра бесплатности."""
    logger.debug(f"User {target.from_user.id} открыл {'бесплатные' if is_free else 'платные'} события")

    offset = (page - 1) * EVENTS_PER_PAGE
    events = (
        await session.execute(
            select(Events)
            .where(Events.date >= date.today(), Events.is_free == is_free)
            .order_by(Events.date.asc())
            .offset(offset)
            .limit(EVENTS_PER_PAGE)
        )
    ).scalars().all()

    total = (
        await session.execute(
            select(func.count(Events.id)).where(Events.date >= date.today(), Events.is_free == is_free)
        )
    ).scalar_one()

    total_pages = max((total + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE, 1)

    if not events:
        text = "❌ События не найдены"
        if isinstance(target, CallbackQuery):
            await safe_edit_message(target.message, text)
            await target.answer()
        else:
            await target.answer(text)
        return

    text = f"📋 <b>Список {'бесплатных' if is_free else 'платных'} событий:</b>\n\n"
    kb = get_events_keyboard(events, page, total_pages, is_free)

    if isinstance(target, CallbackQuery):
        if edit:
            await safe_edit_message(target.message, text, kb)
        else:
            await target.message.delete()
            await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


async def render_event_card(callback: CallbackQuery, session: AsyncSession, event_id: int, page: int, is_free: bool) -> None:
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
    date_line = f"🗓 {event.date:%d.%m.%Y %H:%M}\n\n" if getattr(event, "date", None) else ""
    text = f"<b>{event.name if event.title == '' else event.title} | {event.age_limits}+ </b>\n\n{date_line}{short_desc}"

    kb = get_event_card_keyboard(event, page, is_free, is_tracking=is_tracking)

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


async def render_event_detail(callback: CallbackQuery, session: AsyncSession, event_id: int, page: int, is_free: bool) -> None:
    """Рендер детального описания события."""
    logger.debug("Открытие детального описания события: event_id=%s, page=%s", event_id, page)

    event = await orm_get_event(session, event_id)
    if not event:
        logger.warning("Событие не найдено: %s", event_id)
        await callback.answer("Событие не найдено", show_alert=True)
        return

    text = (
        f"<b>{event.name if event.title == '' else event.title} | {event.age_limits}+</b>\n\n"
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

    kb = get_event_detail_keyboard(event, page, is_free, is_tracking=is_tracking)

    await safe_edit_message(callback.message, text, kb)
    await callback.answer()


# ---------- Хендлеры ----------

@event_router.message(Command("events"))
async def events_command(message: Message) -> None:
    logger.info("Пользователь %s вызвал команду /events", message.from_user.id)
    await render_category_menu(message)


@event_router.callback_query(F.data == "events_new_message")
async def events_category_handler(callback: CallbackQuery) -> None:
    await callback.message.answer('Выберите тип мероприятий:', reply_markup=get_category_menu())


@event_router.callback_query(F.data == "events")
async def events_category_handler(callback: CallbackQuery) -> None:
    await render_category_menu(callback)


@event_router.callback_query(F.data.startswith("events_free:"))
async def events_free_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    page = int(callback.data.split(":")[1])
    await render_event_list(callback, session, is_free=True, page=page)


@event_router.callback_query(F.data.startswith("events_paid:"))
async def events_paid_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    page = int(callback.data.split(":")[1])
    await render_event_list(callback, session, is_free=False, page=page)


@event_router.callback_query(F.data.startswith("events_page:"))
async def events_page_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    _, page, is_free = callback.data.split(":")
    await render_event_list(callback, session, is_free=bool(int(is_free)), page=int(page), edit=True)


@event_router.callback_query(F.data.startswith("event_card:"))
async def event_card_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    _, event_id, page, is_free = callback.data.split(":")
    await render_event_card(callback, session, int(event_id), int(page), bool(int(is_free)))


@event_router.callback_query(F.data.startswith("event_detail:"))
async def event_detail_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    _, event_id, page, is_free = callback.data.split(":")
    await render_event_detail(callback, session, int(event_id), int(page), bool(int(is_free)))


@event_router.callback_query(F.data.startswith("track_event:"))
async def track_event_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    _, event_id, page, is_free = callback.data.split(":")
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
    await render_event_detail(callback, session, int(event_id), int(page), bool(int(is_free)))


@event_router.callback_query(F.data.startswith("untrack_event:"))
async def untrack_event_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    _, event_id, page, is_free = callback.data.split(":")
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
    await render_event_detail(callback, session, int(event_id), int(page), bool(int(is_free)))
