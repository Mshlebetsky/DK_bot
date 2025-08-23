from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from database.models import Events
from database.orm_query import (
    orm_add_event,
    orm_update_event,
    orm_delete_event,
    orm_get_events,
    orm_get_event,
    orm_get_event_by_name
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

class DeleteEventFSM(StatesGroup):
    id = State()

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

# --- Меню ---
@admin_events_router.message(F.text == "Редактировать Афишу")
async def admin_events_menu(message: Message):
    await message.answer("Меню управления событиями:", reply_markup=get_admin_events_kb())

# --- Добавление ---
@admin_events_router.callback_query(F.data == "add_event")
async def add_event_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddEventFSM.name)
    await callback.message.answer("Введите название события:")

@admin_events_router.message(AddEventFSM.name)
async def add_event_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddEventFSM.date)
    await message.answer("Введите дату события (в формате ГГГГ-ММ-ДД ЧЧ:ММ):")

@admin_events_router.message(AddEventFSM.date)
async def add_event_date(message: Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("⚠ Неверный формат даты. Введите в виде: 2025-08-20 18:30")
        return
    await state.update_data(date=date)
    await state.set_state(AddEventFSM.description)
    await message.answer("Введите описание события:")

@admin_events_router.message(AddEventFSM.description)
async def add_event_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddEventFSM.link)
    await message.answer("Введите ссылку (или '-' если нет):")

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
    await message.answer("✅ Событие успешно добавлено!", reply_markup=get_admin_events_kb())

# --- Редактирование ---
@admin_events_router.callback_query(F.data == "edit_event")
async def edit_event_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    events = await orm_get_events(session)
    if not events:
        await callback.message.answer("❌ Нет событий для изменения.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=ev.name, callback_data=f"edit_event_{ev.id}")] for ev in events]
    )
    await callback.message.answer("Выберите событие для редактирования:", reply_markup=kb)

@admin_events_router.callback_query(F.data.startswith("edit_event_"))
async def edit_event_choose(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[2])
    await state.update_data(id=event_id)
    await state.set_state(EditEventFSM.field)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data="field_name")],
        [InlineKeyboardButton(text="Дата", callback_data="field_date")],
        [InlineKeyboardButton(text="Описание", callback_data="field_description")],
        [InlineKeyboardButton(text="Ссылка", callback_data="field_link")],
        [InlineKeyboardButton(text="Изображение", callback_data="field_img")],
    ])
    await callback.message.answer("Выберите поле для изменения:", reply_markup=kb)

@admin_events_router.callback_query(F.data.startswith("field_"), EditEventFSM.field)
async def edit_event_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("field_", "")
    await state.update_data(field=field)
    await state.set_state(EditEventFSM.value)
    await callback.message.answer(f"Введите новое значение для поля {field}:")

@admin_events_router.message(EditEventFSM.value)
async def edit_event_value(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    field, value, event_id = data["field"], message.text, data["id"]

    if field == "date":
        try:
            value = datetime.strptime(value, "%Y-%m-%d %H:%M")
        except ValueError:
            await message.answer("⚠ Неверный формат даты. Введите в виде: 2025-08-20 18:30")
            return
    if field in ("link", "img") and value == "-":
        value = None

    await orm_update_event(session, event_id, {field: value})
    await state.clear()
    await message.answer("✅ Событие успешно изменено!", reply_markup=get_admin_events_kb())

# --- Удаление ---
@admin_events_router.callback_query(F.data == "delete_event")
async def delete_event_start(callback: CallbackQuery, session: AsyncSession):
    events = await orm_get_events(session)
    if not events:
        await callback.message.answer("❌ Нет событий для удаления.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=ev.name, callback_data=f"delete_event_{ev.id}")] for ev in events]
    )
    await callback.message.answer("Выберите событие для удаления:", reply_markup=kb)

@admin_events_router.callback_query(F.data.startswith("delete_event_"))
async def delete_event_confirm(callback: CallbackQuery, session: AsyncSession):
    event_id = int(callback.data.split("_")[2])
    await orm_delete_event(session, event_id)
    await callback.message.answer("🗑 Событие удалено!", reply_markup=get_admin_events_kb())

# --- Список событий ---
EVENTS_PER_PAGE = 8

def get_events_keyboard(events, page: int, total_pages: int):
    keyboard = [
        [InlineKeyboardButton(text=ev.name, callback_data=f"event_detail:{ev.id}:{page}")] for ev in events
    ]
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⏮ Назад", callback_data=f"events_page:{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="⏭ Далее", callback_data=f"events_page:{page+1}"))
    if nav:
        keyboard.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@admin_events_router.callback_query(F.data == "list_events")
async def list_events(callback: CallbackQuery, session: AsyncSession, page: int = 1):
    PAGE_SIZE = EVENTS_PER_PAGE
    offset = (page - 1) * PAGE_SIZE
    events = (await session.execute(select(Events).offset(offset).limit(PAGE_SIZE))).scalars().all()
    total = (await session.execute(select(func.count(Events.id)))).scalar_one()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    if not events:
        await callback.message.answer("События не найдены")
        return

    text = "<b>Список событий:</b>\n\n" + "\n".join([f"▫️ {ev.name}" for ev in events])
    await callback.message.edit_text(text, reply_markup=get_events_keyboard(events, page, total_pages))

@admin_events_router.callback_query(F.data.startswith("events_page:"))
async def events_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await list_events(callback, session, page)

@admin_events_router.callback_query(F.data.startswith("event_detail:"))
async def event_detail_handler(callback: CallbackQuery, session: AsyncSession):
    event_id = int(callback.data.split(":")[1])
    event = await orm_get_event(session, event_id)
    if not event:
        await callback.answer("Событие не найдено", show_alert=True)
        return

    text = (
        f"<b>{event.name}</b>\n\n"
        f"📅 Дата: {event.date.strftime('%d.%m.%Y %H:%M') if event.date else '—'}\n"
        f"🔗 Ссылка: {event.link or '—'}\n\n"
        f"ℹ️ {event.description}"
    )
    if event.img:
        try:
            await callback.message.answer_photo(event.img, caption=event.name[:100])
        except Exception:
            await callback.message.answer(f"📷 <b>{event.name}</b>")
    await callback.message.answer(text)
    await callback.answer()

# --- Обновление всех ---
@admin_events_router.callback_query(F.data == "update_all_events")
async def update_all_events_handler(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer("🔄 Запускаю обновление событий, подождите...")
    try:
        data, log_text = update_all_events()
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при парсинге: {e}")
        return

    updated, added = 0, 0
    for name, values in data.items():
        try:
            event_date, description, img, link = values
        except ValueError:
            continue

        event = await orm_get_event_by_name(session, name)
        if event:
            event.date = event_date
            event.description = description
            event.img = img
            event.link = link
            updated += 1
        else:
            new_event = Events(
                name=name, date=event_date, description=description,
                img=img, link=link, is_shown=True
            )
            session.add(new_event)
            added += 1
    await session.commit()

    await callback.message.answer(
        f"{log_text}\n\n🔄 Обновлено: {updated}\n➕ Добавлено: {added}",
        reply_markup=get_admin_events_kb()
    )
