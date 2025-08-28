from datetime import date

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, insert, delete

from database.models import Events, UserEventTracking
from database.orm_query import orm_get_event

event_router = Router()
EVENTS_PER_PAGE = 8


# ---------- Клавиатуры ----------
def get_events_keyboard(events, page: int, total_pages: int):
    keyboard = [
        [InlineKeyboardButton(
            text=f"🗓 {ev.date:%d.%m} | {ev.name[:30]}+ | +{ev.age_limits}",
            callback_data=f"event_card:{ev.id}:{page}"
        )]
        for ev in events
    ]

    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⏮ Назад", callback_data=f"events_page:{page-1}")
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="⏭ Далее", callback_data=f"events_page:{page+1}")
        )
    if nav_buttons:
        keyboard.append(nav_buttons)
        keyboard.append([InlineKeyboardButton(text="🏠 В Главное меню", callback_data='main_menu')])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_event_card_keyboard(event_id: int, page: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"events_page:{page}")],
        [InlineKeyboardButton(text="ℹ Подробнее", callback_data=f"event_detail:{event_id}")],
        [InlineKeyboardButton(text="🔗 Перейти на сайт", url="https://дк-яуза.рф/afisha/")],
    ])


def get_event_detail_keyboard(event: Events, page: int, is_tracking: bool = False):
    buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data=f"events_page:{page}")],
               [InlineKeyboardButton(text="🔗 Перейти на сайт", url="https://дк-яуза.рф/afisha/")],
               ]

    if event.link:
        buttons.append([InlineKeyboardButton(text="📝 Приобрести билеты", url=event.link)])

    # 👇 Добавляем кнопку отслеживания
    if is_tracking:
        buttons.append([InlineKeyboardButton(text="✅ Отслеживается", callback_data=f"untrack_event:{event.id}:{page}")])
    else:
        buttons.append([InlineKeyboardButton(text="🔔 Отслеживать", callback_data=f"track_event:{event.id}:{page}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)



# ---------- Рендеры ----------
# ---------- Рендер списка ----------
async def render_event_list(target: Message | CallbackQuery, session: AsyncSession, page: int = 1, edit: bool = False):
    offset = (page - 1) * EVENTS_PER_PAGE
    events = (
        await session.execute(
            select(Events)
            .where(Events.date >= date.today())  # 👈 только будущие события
            .order_by(Events.date.asc())
            .offset(offset)
            .limit(EVENTS_PER_PAGE)
        )
    ).scalars().all()

    total = (
        await session.execute(
            select(func.count(Events.id)).where(Events.date >= date.today())
        )
    ).scalar_one()

    total_pages = (total + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE

    if not events:
        text = "❌ События не найдены"
        if isinstance(target, CallbackQuery):
            if edit:
                await target.message.edit_text(text)
            else:
                await target.message.answer(text)
            await target.answer()
        else:
            await target.answer(text)
        return

    text = "📋 <b>Список ближайших событий:</b>\n\n"
    kb = get_events_keyboard(events, page, total_pages)

    if isinstance(target, CallbackQuery):
        if edit:  # пагинация
            try:
                await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                # бывает, если сообщение было с фото → удаляем и шлём новое
                await target.message.delete()
                await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:  # первый вызов
            try:
                await target.message.delete()
            except Exception:
                pass
            await target.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")



async def render_event_card(callback: CallbackQuery, session: AsyncSession, event_id: int, page: int):
    event = await orm_get_event(session, event_id)
    if not event:
        await callback.answer("Событие не найдено", show_alert=True)
        return

    desc = event.description or "Нет описания"
    short_desc = desc[:500] + ("…" if len(desc) > 500 else "")
    date_line = f"🗓 {event.date:%d.%m.%Y}\n\n" if getattr(event, "date", None) else ""
    text = f"<b>{event.name} | +{event.age_limits}</b>\n\n{date_line}{short_desc}"

    kb = get_event_card_keyboard(event.id, page)

    try:
        await callback.message.delete()
    except Exception:
        pass

    if event.img:
        await callback.message.answer_photo(event.img, caption=text[:1024], reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

    await callback.answer()


async def render_event_detail(callback: CallbackQuery, session: AsyncSession, event_id: int, page: int):
    event = await orm_get_event(session, event_id)
    if not event:
        await callback.answer("Событие не найдено", show_alert=True)
        return

    text = (
        f"<b>{event.name} | +{event.age_limits}</b>\n\n"
        f"🗓 {event.date:%d.%m.%Y}\n\n"
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

    try:
        await callback.message.delete()
    except Exception:
        pass

    if event.img:
        await callback.message.answer_photo(event.img, caption=text[:1024], reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

    await callback.answer()



# ---------- Хендлеры ----------
@event_router.message(Command("event_list"))
async def cmd_event_list(message: Message, session: AsyncSession):
    await render_event_list(message, session, page=1)


@event_router.callback_query(F.data == "list_events")
async def list_events_handler(callback: CallbackQuery, session: AsyncSession):
    await render_event_list(callback, session, page=1)


@event_router.callback_query(F.data.startswith("events_page:"))
async def events_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await render_event_list(callback, session, page, edit=True)


@event_router.callback_query(F.data.startswith("event_card:"))
async def event_card_handler(callback: CallbackQuery, session: AsyncSession):
    _, event_id, page = callback.data.split(":")
    await render_event_card(callback, session, int(event_id), int(page))


@event_router.callback_query(F.data.startswith("event_detail:"))
async def event_detail_handler(callback: CallbackQuery, session: AsyncSession):
    _, event_id = callback.data.split(":")
    # сюда передаём page=1, либо можно прокидывать динамически
    await render_event_detail(callback, session, int(event_id), page=1)

@event_router.callback_query(F.data.startswith("track_event:"))
async def track_event_handler(callback: CallbackQuery, session: AsyncSession):
    _, event_id, page = callback.data.split(":")
    user_id = callback.from_user.id

    # Проверка, не отслеживает ли уже
    existing = await session.execute(
        select(UserEventTracking).where(
            UserEventTracking.user_id == user_id,
            UserEventTracking.event_id == int(event_id)
        )
    )
    if not existing.scalars().first():
        session.add(UserEventTracking(user_id=user_id, event_id=int(event_id)))
        await session.commit()

    await callback.answer("✅ Вы подписались на напоминания")
    await render_event_detail(callback, session, int(event_id), int(page))


@event_router.callback_query(F.data.startswith("untrack_event:"))
async def untrack_event_handler(callback: CallbackQuery, session: AsyncSession):
    _, event_id, page = callback.data.split(":")
    user_id = callback.from_user.id

    await session.execute(
        delete(UserEventTracking).where(
            UserEventTracking.user_id == user_id,
            UserEventTracking.event_id == int(event_id)
        )
    )
    await session.commit()

    await callback.answer("❌ Напоминание снято")
    await render_event_detail(callback, session, int(event_id), int(page))