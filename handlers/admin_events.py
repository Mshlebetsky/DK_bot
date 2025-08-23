from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import (
    orm_add_event, orm_get_events, orm_get_event,
    orm_update_event, orm_delete_event
)
from handlers.user_private import Admin_Default_KBRD
from replyes.kbrds import get_keyboard
from aiogram.filters import Command, or_f
from datetime import datetime
admin_events_router = Router()


# Меню


studio_buttons= [
    "➕ Добавить мероприятие",
    "✏️ Изменить мероприятие",
    "❌ Удалить мероприятие",
    "📋 Все мероприятия",
    "🔄Обновить все мероприятия",
    "🛠Панель администратора"
]
admin_events_kbrd = get_keyboard(*studio_buttons, placeholder='',sizes=(3,3))

@admin_events_router.message(or_f(Command('admin_studios'), F.text == 'Редактировать Афишу'))
async def admin_studios_menu(message: types.Message):
    try:
        await state.clear()
    except:
        pass
    await message.answer('Админ: Студии\nДоступно: /studios_list, /studio_add, /studio_del <id>, /studio_edit <id>',
                         reply_markup= admin_events_kbrd)


# FSM для добавления/редактирования
class EventForm(StatesGroup):
    name = State()
    description = State()
    date = State()
    link = State()
    is_free = State()
    img = State()
    is_shown = State()
    announsed = State()
    confirm = State()

# ➕ Добавление мероприятия
@admin_events_router.message(F.text == "➕ Добавить мероприятие")
async def add_event(message: types.Message, state: FSMContext):
    await state.set_state(EventForm.name)
    await message.answer("Введите название мероприятия:")


@admin_events_router.message(EventForm.name)
async def set_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(EventForm.description)
    await message.answer("Введите описание мероприятия:")


@admin_events_router.message(EventForm.description)
async def set_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(EventForm.date)
    await message.answer("Введите дату мероприятия (в формате ДД.ММ.ГГГГ ЧЧ:ММ):")




@admin_events_router.message(EventForm.date)
async def set_event_date(message: types.Message, state: FSMContext):
    try:
        # Пробуем распарсить в формате 31.12.2025 18:30
        event_date = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        await state.update_data(date=event_date)   # <-- сохраняем объект datetime
        await message.answer("Введите ссылку на мероприятие (или '-' если нет):")
        await state.set_state(EventForm.link)
    except ValueError:
        await message.answer("⚠️ Неверный формат даты!\nПопробуй так: 31.12.2025 18:30")


@admin_events_router.message(EventForm.link)
async def set_link(message: types.Message, state: FSMContext):
    link = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(link=link)
    await state.set_state(EventForm.is_free)
    await message.answer("Мероприятие бесплатное? (да/нет)")


@admin_events_router.message(EventForm.is_free)
async def set_is_free(message: types.Message, state: FSMContext):
    is_free = message.text.lower() in ["да", "yes", "y", "true", "1"]
    await state.update_data(is_free=is_free)
    await state.set_state(EventForm.img)
    await message.answer("Пришлите ссылку на изображение мероприятия (или '-' если нет):")


@admin_events_router.message(EventForm.img)
async def set_img(message: types.Message, state: FSMContext):
    img = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(img=img)
    await state.set_state(EventForm.is_shown)
    await message.answer("Показывать мероприятие пользователям? (да/нет)")


@admin_events_router.message(EventForm.is_shown)
async def set_is_shown(message: types.Message, state: FSMContext):
    is_shown = message.text.lower() in ["да", "yes", "y", "true", "1"]
    await state.update_data(is_shown=is_shown)
    await state.set_state(EventForm.announsed)
    await message.answer("Мероприятие анонсировано? (да/нет)")


@admin_events_router.message(EventForm.announsed)
async def set_announsed(message: types.Message, state: FSMContext, session: AsyncSession):
    announsed = message.text.lower() in ["да", "yes", "y", "true", "1"]
    await state.update_data(announsed=announsed)

    data = await state.get_data()
    text = (
        f"<b>{data['name']}</b>\n"
        f"{data["description"]}\n\n"
        f"📅 {data['date']}\n"
        f"🔗 {data['link'] if data['link'] else '—'}\n"
        f"💰 {'Бесплатное' if data['is_free'] else 'Платное'}\n"
        f"👁 {'Показывается' if data['is_shown'] else 'Скрыто'} | "
        f"📢 {'Анонсировано' if data['announsed'] else 'Не анонсировано'}"
    )
    await message.answer(text, parse_mode="HTML")
    await state.set_state(EventForm.confirm)
    await message.answer("Подтвердить добавление?")

@admin_events_router.message(EventForm.confirm)
async def confirm_add(message: types.Message, state: FSMContext, session: AsyncSession):
    announsed = message.text.lower() in ["да", "yes", "y", "true", "1"]
    if announsed:
        data = await state.get_data()
        event = await orm_add_event(session, data)
        await state.clear()

        text = (
            f"✅ Мероприятие добавлено!\n\n"
            f"<b>{event.name}</b>\n"
            f"{event.description}\n\n"
            f"📅 {event.date}\n"
            f"🔗 {event.link if event.link else '—'}\n"
            f"💰 {'Бесплатное' if event.is_free else 'Платное'}\n"
            f"👁 {'Показывается' if event.is_shown else 'Скрыто'} | "
            f"📢 {'Анонсировано' if event.announsed else 'Не анонсировано'}"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=admin_events_kbrd)
    else:
        await state.clear()
        await message.answer(f'Добавление отменено', reply_markup=admin_events_kbrd)

# 📋 Список мероприятий
@admin_events_router.message(F.text == "📋 Все мероприятия")
async def list_events(message: types.Message, session: AsyncSession):
    events = await orm_get_events(session)
    if not events:
        await message.answer("❌ Мероприятий пока нет", reply_markup=admin_events_kbrd)
        return

    text = "📌 <b>Список мероприятий:</b>\n\n"
    for ev in events:
        text += f"ID: {ev.id} | {ev.name} ({ev.date.day}\t {ev.date.month})\n"

    await message.answer(text, parse_mode="HTML")


# 🔄 Редактирование мероприятия
class EditEventForm(EventForm):
    id = State()


@admin_events_router.message(F.text == "✏️ Изменить мероприятие")
async def choose_event(message: types.Message, state: FSMContext, session: AsyncSession):
    events = await orm_get_events(session)
    if not events:
        await message.answer("❌ Нет мероприятий для редактирования")
        return

    text = "Введите ID мероприятия для изменения:\n\n"
    for ev in events:
        text += f"ID: {ev.id} | {ev.name} | {ev.date}\n"

    await state.set_state(EditEventForm.id)
    await message.answer(text)


@admin_events_router.message(EditEventForm.id)
async def start_edit(message: types.Message, state: FSMContext, session: AsyncSession):
    if type(message.text)  is int:
        await message.answer("❌ Введите корректный ID!")
        return
    event_id = int(message.text)
    event = await orm_get_event(session, event_id)
    if not event:
        await message.answer("❌ Мероприятие не найдено")
        return

    await state.update_data(id=event_id)
    await state.set_state(EditEventForm.name)
    await message.answer(f"Изменяем мероприятие: <b>{event.name}</b>\n\nВведите новое название:", parse_mode="HTML")


# ❌ Удаление
@admin_events_router.message(F.text == "❌ Удалить мероприятие")
async def delete_event_start(message: types.Message, session: AsyncSession, state: FSMContext):
    events = await orm_get_events(session)
    if not events:
        await message.answer("❌ Нет мероприятий для удаления")
        return

    text = "Введите ID мероприятия для удаления:\n\n"
    for ev in events:
        text += f"ID: {ev.id} | {ev.name}\n"

    await state.set_state("delete_event_id")
    await message.answer(text)


@admin_events_router.message(F.text.regexp(r"^\d+$"), StateFilter("delete_event_id"))
async def confirm_delete(message: types.Message, state: FSMContext, session: AsyncSession):
    event_id = int(message.text)
    await orm_delete_event(session, event_id)
    await state.clear()
    await message.answer("✅ Мероприятие удалено")
