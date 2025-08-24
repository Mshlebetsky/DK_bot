from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func


from database import orm_query
from database.models import Events
from database.orm_query import (
    orm_add_event, orm_update_event, orm_delete_event,
    orm_get_events, orm_get_event_by_name
)
from logic.scrap_events import update_all_events

admin_events_router = Router()

# --- FSM ---
class AddEventFSM(StatesGroup):
    name = State()
    date = State()
    description = State()
    link = State()
    img = State()

class EditEventFSM(StatesGroup):
    id = State()
    field = State()
    value = State()


# --- Клавиатуры ---
def get_admin_events_kb():
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить событие", callback_data="add_event")],
        [InlineKeyboardButton(text="✏️ Изменить событие", callback_data="edit_event")],
        [InlineKeyboardButton(text="🗑 Удалить событие", callback_data="delete_event")],
        [InlineKeyboardButton(text="📋 Список событий", callback_data="list_events")],
        [InlineKeyboardButton(text="🔄 Обновить все события", callback_data="update_all_events")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Стартовое меню ---
@admin_events_router.message(F.text == "Редактировать Афишу")
async def admin_events_menu(message: Message):
    await message.answer("Меню управления событиями:", reply_markup=get_admin_events_kb())

# --- Добавление события ---
@admin_events_router.callback_query(F.data == "add_event")
async def add_event_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddEventFSM.name)
    await callback.message.answer("Введите название события:")

@admin_events_router.message(AddEventFSM.name)
async def add_event_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddEventFSM.date)
    await message.answer("Введите дату события (в формате ГГГГ-ММ-ДД ЧЧ:ММ\n'-' если хотите выйти из меню добавления события):")

@admin_events_router.message(AddEventFSM.date)
async def add_event_date(message: Message, state: FSMContext):
    from datetime import datetime
    if message.text == "-":
        await state.clear()
        return
    try:
        event_date = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат даты. Введите в формате: 2025-08-21 18:30")
        return
    await state.update_data(date=event_date)
    await state.set_state(AddEventFSM.description)
    await message.answer("Введите описание события:")

@admin_events_router.message(AddEventFSM.description)
async def add_event_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddEventFSM.link)
    await message.answer("Введите ссылку на событие (или '-' если нет):")

@admin_events_router.message(AddEventFSM.link)
async def add_event_link(message: Message, state: FSMContext):
    link = None if message.text == "-" else message.text
    await state.update_data(link=link)
    await state.set_state(AddEventFSM.img)
    await message.answer("Отправьте ссылку на изображение (или '-' если нет):")

@admin_events_router.message(AddEventFSM.img)
async def add_event_img(message: Message, state: FSMContext, session: AsyncSession):
    img = None if message.text == "-" else message.text
    await state.update_data(img=img)
    data = await state.get_data()
    await orm_add_event(session, data)
    await state.clear()
    await message.answer("✅ Событие добавлено!", reply_markup=get_admin_events_kb())

# --- Изменение события ---
@admin_events_router.callback_query(F.data == "edit_event")
async def edit_event_start(callback: CallbackQuery, session: AsyncSession):
    events = await orm_get_events(session)
    if not events:
        await callback.message.answer("❌ Нет событий для изменения.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=e.name, callback_data=f"edit_event_{e.id}")] for e in events
    ])
    await callback.message.answer("Выберите событие:", reply_markup=kb)

@admin_events_router.callback_query(F.data.startswith("edit_event_"))
async def edit_event_choose(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[2])
    await state.update_data(id=event_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data="field_name")],
        [InlineKeyboardButton(text="Дата", callback_data="field_date")],
        [InlineKeyboardButton(text="Описание", callback_data="field_description")],
        [InlineKeyboardButton(text="Ссылка", callback_data="field_link")],
        [InlineKeyboardButton(text="Изображение", callback_data="field_img")],
    ])
    await state.set_state(EditEventFSM.field)
    await callback.message.answer("Выберите поле для изменения:", reply_markup=kb)

@admin_events_router.callback_query(F.data.startswith("field_"), EditEventFSM.field)
async def edit_event_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("field_", "")
    await state.update_data(field=field)
    await state.set_state(EditEventFSM.value)
    await callback.message.answer(f"Введите новое значение для поля {field}:")

@admin_events_router.message(EditEventFSM.value)
async def edit_event_value(message: Message, state: FSMContext, session: AsyncSession):
    from datetime import datetime
    data = await state.get_data()
    field = data["field"]
    value = message.text
    if field == "date":
        try:
            value = datetime.strptime(value, "%Y-%m-%d %H:%M")
        except ValueError:
            await message.answer("❌ Формат даты: 2025-08-21 18:30")
            return
    await orm_update_event(session, data["id"], {field: value})
    await state.clear()
    await message.answer("✅ Событие изменено!", reply_markup=get_admin_events_kb())

# --- Удаление события ---
@admin_events_router.callback_query(F.data == "delete_event")
async def delete_event_start(callback: CallbackQuery, session: AsyncSession):
    events = await orm_get_events(session)
    if not events:
        await callback.message.answer("❌ Нет событий для удаления.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=e.name, callback_data=f"delete_event_{e.id}")] for e in events
    ])
    await callback.message.answer("Выберите событие:", reply_markup=kb)

@admin_events_router.callback_query(F.data.startswith("delete_event_"))
async def delete_event_confirm(callback: CallbackQuery, session: AsyncSession):
    event_id = int(callback.data.split("_")[2])
    await orm_delete_event(session, event_id)
    await callback.message.answer("🗑 Событие удалено!", reply_markup=get_admin_events_kb())

# --- Список событий ---
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

@admin_events_router.message(F.text.in_({"📋 Список событий","Список событий", "Список мероприятий"}))
async def events_list_command(message: types.Message, session: AsyncSession):
    await list_events(message, session, page=1)
@admin_events_router.callback_query(F.data.in_({"list_events", "events_list"}))
async def events_list_callback(callback: types.CallbackQuery, session: AsyncSession):
    await list_events(callback, session, page=1)

# пагинация
@admin_events_router.callback_query(F.data.startswith("events_page:"))
async def events_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await list_events(callback, session, page)


# карточка события (краткая)
@admin_events_router.callback_query(F.data.startswith("event_card:"))
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
@admin_events_router.callback_query(F.data.startswith("event_detail:"))
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

# --- Обновить все события ---
@admin_events_router.callback_query(F.data == "update_all_events")
async def update_all_events_handler(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer("🔄 Запускаю обновление афиши, пожалуйста подождите...\nПримерное время обновления ~2-3 минуты")

    try:
        data, log_text = await asyncio.to_thread(update_all_events)
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка парсера: {e}")
        return

    updated, added = 0, 0
    from datetime import datetime
    for name, values in data.items():
        try:
            event_date, description, img, link = values
        except ValueError:
            await callback.message.answer(f"⚠ Ошибка формата данных: {name}")
            continue

        event = await orm_query.orm_get_event_by_name(session, name)
        if event:
            await orm_update_event(session, event.id, {
                "date": datetime.strptime(event_date, "%Y-%m-%d %H:%M"),
                "description": description,
                "img": img,
                "link": link
            })
            updated += 1
        else:
            await orm_add_event(session, {
                "name": name,
                "date": datetime.strptime(event_date, "%Y-%m-%d %H:%M"),
                "description": description,
                "img": img,
                "link": link
            })
            added += 1

    await callback.message.answer(
        f"{log_text}\n\n"
        f"🔄 Обновлено: {updated}\n"
        f"➕ Добавлено: {added}",
        reply_markup=get_admin_events_kb()
    )