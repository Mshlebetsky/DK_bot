import asyncio

from aiogram import Router, F, types, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import or_f,Command

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from sqlalchemy.ext.asyncio import AsyncSession


from database import orm_query
from database.orm_query import (
    orm_add_event, orm_update_event, orm_delete_event,
    orm_get_events, orm_get_event_by_name
)
from logic.scrap_events import update_all_events, find_age_limits
from handlers.notification import notify_subscribers
from filter.filter import check_message, IsAdmin, ChatTypeFilter

admin_events_router = Router()
admin_events_router.message.filter(ChatTypeFilter(['private']),IsAdmin())
# --- FSM ---
class AddEventFSM(StatesGroup):
    name = State()
    date = State()
    description = State()
    link = State()
    img = State()
    notify = State()

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
@admin_events_router.message(or_f((F.text == "Редактировать Афишу"),Command('edit_events')))
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
    age_limit = find_age_limits(message.text)
    await state.update_data(description=message.text)
    await state.update_data(age_limits = age_limit)
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
    await state.set_state(AddEventFSM.notify)
    await message.answer(f"✅ Событие добавлено!\n\nХотите оповестить об этом пользователей?(Да/нет)")

@admin_events_router.message(AddEventFSM.notify)
async def add_event_anounse(message: Message, state: FSMContext, session: AsyncSession,bot : Bot):
    anouncement = True if message.text.lower() in ['yes', 'да', 1] else False
    if anouncement:
        data = await state.get_data()
        await notify_subscribers(bot, session, f"📰 Новое мероприятие: {data['name']} \n\n{data['date']}", data['img'], type_="events")
        await message.answer('👍Уведомление пользователям успешно отправлено', reply_markup=get_admin_events_kb())
    else:
        await message.answer('👍Мероприятие успешно добавлено без оповещения пользователей', reply_markup=get_admin_events_kb())
    await state.clear()


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

# --- Обновить все события ---
@admin_events_router.callback_query(F.data == "update_all_events")
async def update_all_events_handler_(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    question_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="C оповещением пользователей", callback_data=f"update_all_events_True")],
        [InlineKeyboardButton(text="Без оповещения пользователей", callback_data=f"update_all_events_False")]
    ])
    await callback.message.answer("Оповестить пользователей?", reply_markup=question_kb)
@admin_events_router.callback_query(F.data.startswith("update_all_events_"))
async def update_all_events_handler(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    try:
        update = (callback.data.split('_')[3] == str(True))
    except:
        update = False
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
            event_date, description, age_limits, img, link = values
        except ValueError:
            await callback.message.answer(f"⚠ Ошибка формата данных: {name}")
            continue

        event = await orm_query.orm_get_event_by_name(session, name)
        if event:
            await orm_update_event(session, event.id, {
                "date": datetime.strptime(event_date, "%Y-%m-%d %H:%M"),
                "description": description,
                "age_limits" : age_limits,
                "img": img,
                "link": link
            })
            updated += 1
        else:
            await orm_add_event(session, {
                "name": name,
                "date": datetime.strptime(event_date, "%Y-%m-%d %H:%M"),
                "description": description,
                "age_limits": age_limits,
                "img": img,
                "link": link
            })
            added += 1
            if update:
                text = f"{str(update)}\n{name.capitalize()} | +{age_limits}\n\n{event_date}"
                await notify_subscribers(bot, session, f"📰 Обновление в афише! \n\n{text}", img, type_="events")
    await callback.message.answer(
        f"{log_text}\n\n"
        f"🔄 Обновлено: {updated}\n"
        f"➕ Добавлено: {added}",
        reply_markup=get_admin_events_kb()
    )