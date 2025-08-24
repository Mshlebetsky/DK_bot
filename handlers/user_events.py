from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import or_f, Command
from database.models import Events
from sqlalchemy import select, func


user_events_router = Router()

@user_events_router.message(or_f(Command('events'),(F.text == "📆Афиша мероприятий")))
async def events_list_command(message: types.Message, session: AsyncSession):
    await list_events(message, session, page=1)

EVENTS_PER_PAGE = 8

def get_events_keyboard(events, page: int, total_pages: int):
    """Клавиатура для списка событий"""
    keyboard = [
        [InlineKeyboardButton( text=f"{ev.date:%d.%m} | {ev.name[:30].capitalize()}", callback_data=f"event_card:{ev.id}:{page}")]
        for ev in events
    ]
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⏮ Назад", callback_data=f"events_page:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="⏭ Далее", callback_data=f"events_page:{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def list_events(message_or_callback, session: AsyncSession, page: int = 1):
    offset = (page - 1) * EVENTS_PER_PAGE
    events = (
        await session.execute(
            select(Events)
            .offset(offset)
            .limit(EVENTS_PER_PAGE)
            .order_by(Events.date.asc())
        )
    ).scalars().all()

    total = (await session.execute(select(func.count(Events.id)))).scalar_one()
    total_pages = (total + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE

    if not events:
        target = message_or_callback.message if isinstance(message_or_callback, types.CallbackQuery) else message_or_callback
        await target.answer("События не найдены")
        if isinstance(message_or_callback, types.CallbackQuery):
            await message_or_callback.answer()
        return

    # text = "<b>Список событий:</b>\n\n" + "\n".join(f"▫️ {ev.name}" for ev in events)
    text = "<b>📋 Список ближайших событий:</b>\n\n"
    kb = get_events_keyboard(events, page, total_pages)

    if isinstance(message_or_callback, types.CallbackQuery):
        msg = message_or_callback.message
        try:
            if msg.text:  # обычный текст — редактируем текст
                await msg.edit_text(text, reply_markup=kb, ParseMode="HTML")
            elif msg.caption is not None:
                # это медиа — надёжнее удалить и отправить новый список как текст
                try:
                    await msg.delete()
                except Exception:
                    pass
                await msg.answer(text, reply_markup=kb)
            else:
                # на всякий случай
                await msg.answer(text, reply_markup=kb)
        except Exception:
            # общий фоллбек
            await msg.answer(text, reply_markup=kb)
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(text, reply_markup=kb)

# --- Хендлеры ---

# команда для списка

@user_events_router.message(F.text.in_({"📋 Список событий","Список событий", "Список мероприятий"}))
async def events_list_command(message: types.Message, session: AsyncSession):
    await list_events(message, session, page=1)
@user_events_router.callback_query(F.data.in_({"list_events", "events_list"}))
async def events_list_callback(callback: types.CallbackQuery, session: AsyncSession):
    await list_events(callback, session, page=1)

# пагинация
@user_events_router.callback_query(F.data.startswith("events_page:"))
async def events_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await list_events(callback, session, page)


# карточка события (краткая)
@user_events_router.callback_query(F.data.startswith("event_card:"))
async def event_card_handler(callback: CallbackQuery, session: AsyncSession):
    _, event_id, page = callback.data.split(":")
    event = await session.get(Events, int(event_id))
    if not event:
        await callback.answer("Событие не найдено", show_alert=True)
        return

    desc = event.description or "Нет описания"
    short_desc = (desc[:500] + "…") if len(desc) > 500 else desc
    date_line = f"🗓 {event.date:%d.%m.%Y}\n\n" if getattr(event, "date", None) else ""
    text = f"<b>{event.name}</b>\n\n{date_line}{short_desc}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"events_page:{page}")],
        [InlineKeyboardButton(text="ℹ️ Подробнее", callback_data=f"event_detail:{event.id}")]
    ])

    # удаляем список и шлём карточку
    try:
        await callback.message.delete()
    except Exception:
        pass

    if getattr(event, "img", None):
        await callback.message.answer_photo(event.img, caption=text, reply_markup=kb)
    else:
        await callback.message.answer(text, reply_markup=kb)

    await callback.answer()


# полная карточка
@user_events_router.callback_query(F.data.startswith("event_detail:"))
async def event_detail_handler(callback: CallbackQuery, session: AsyncSession):
    event_id = int(callback.data.split(":")[1])
    event = await session.get(Events, event_id)
    if not event:
        await callback.answer("Событие не найдено", show_alert=True)
        return

    text = (
        f"<b>{event.name}</b>\n\n"
        f"🗓 {event.date:%d.%m.%Y}\n\n"
        f"{event.description}\n"
    )

    # kb = [[InlineKeyboardButton(text="🔙 Назад к списку", callback_data="events_page:1")]]
    kb = [[InlineKeyboardButton(text="🔙 Назад к списку", callback_data="events_page:1")]]

    if event.link:
        kb.append([InlineKeyboardButton(text="📝 Записаться", url=event.link)])

    if event.img:
        try:
            await callback.message.answer_photo(event.img, caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        except Exception:
            await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    await callback.answer()
