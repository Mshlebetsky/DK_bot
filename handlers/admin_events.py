"""
Обработчики панели администратора для управления событиями (Events).
"""

import asyncio
import logging
from datetime import datetime

from aiogram import Router, F, types, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import or_f, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from pyexpat.errors import messages
from sqlalchemy.ext.asyncio import AsyncSession

from database import orm_query
from database.orm_query import (
    orm_add_event,
    orm_update_event,
    orm_delete_event,
    orm_get_events,
    orm_get_event_by_name,
)
from logic.scrap_events import update_all_events, find_age_limits
from handlers.notification import notify_subscribers
from filter.filter import IsEditor, IsSuperAdmin


# ================== ЛОГИРОВАНИЕ ==================

logger = logging.getLogger(__name__)

# ================== РОУТЕР ==================
admin_events_router = Router()
admin_events_router.message.filter(or_f(IsSuperAdmin(), IsEditor()))


# ================== FSM ==================
class AddEventFSM(StatesGroup):
    """Состояния для добавления события."""
    name = State()
    is_free = State()
    date = State()
    description = State()
    link = State()
    img = State()
    notify = State()


class EditEventFSM(StatesGroup):
    """Состояния для редактирования события."""
    id = State()
    field = State()
    value = State()


# ================== КНОПКИ ==================
def get_admin_events_kb() -> InlineKeyboardMarkup:
    """Клавиатура меню управления событиями."""
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить событие", callback_data="add_event")],
        [InlineKeyboardButton(text="✏️ Изменить событие", callback_data="edit_event")],
        [InlineKeyboardButton(text="🗑 Удалить событие", callback_data="delete_event")],
        [InlineKeyboardButton(text="📋 Список событий", callback_data="list_events")],
        [InlineKeyboardButton(text="🔄 Обновить все события", callback_data="update_all_events")],
        [InlineKeyboardButton(text="🛠 В панель администратора", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ================== МЕНЮ ==================
@admin_events_router.message(Command("edit_events"))
@admin_events_router.callback_query(F.data == "edit_events_panel")
async def show_admin_events_menu(event: types.Message | CallbackQuery) -> None:
    """Показывает меню управления событиями."""
    target = event.message if isinstance(event, CallbackQuery) else event
    await target.answer("Меню управления событиями:", reply_markup=get_admin_events_kb())
    logger.info(f"Переход в меню управления афиши (user_id={event.from_user.id})")


# ================== ДОБАВЛЕНИЕ СОБЫТИЯ ==================
@admin_events_router.callback_query(F.data == "add_event")
async def add_event_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddEventFSM.name)
    await callback.message.answer("Введите название события:")
    logger.debug("Начато добавление события")


@admin_events_router.message(AddEventFSM.name)
async def add_event_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(AddEventFSM.is_free)
    await message.answer("Мероприятие бесплатное? (Да/нет")
    logger.debug(f"Указано название события: {message.text}")


@admin_events_router.message(AddEventFSM.is_free)
async def add_event_is_free(message: Message, state: FSMContext) -> None:
    is_free = message.text.lower() in ["yes", "да", "1"]
    await state.update_data(is_free=is_free)
    await state.set_state(AddEventFSM.date)
    await message.answer(
        "Введите дату события (ГГГГ-ММ-ДД ЧЧ:ММ)\n"
        "Или '-' для выхода."
    )
    logger.debug("Указано, бесплатное ли мероприятие")


@admin_events_router.message(AddEventFSM.date)
async def add_event_date(message: Message, state: FSMContext) -> None:
    if message.text == "-":
        await state.clear()
        logger.info("Отмена добавления события по запросу пользователя")
        return
    try:
        event_date = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат даты. Пример: 2025-08-21 18:30")
        return
    await state.update_data(date=event_date)
    await state.set_state(AddEventFSM.description)
    await message.answer("Введите описание события:")
    logger.debug(f"Указана дата события: {event_date}")


@admin_events_router.message(AddEventFSM.description)
async def add_event_description(message: Message, state: FSMContext) -> None:
    age_limit = find_age_limits(message.text)
    await state.update_data(description=message.text, age_limits=age_limit)
    await state.set_state(AddEventFSM.link)
    await message.answer("Введите ссылку на покупку билетов (или '-' если нет или событие бесплатное):")
    logger.debug("Добавлено описание события")


@admin_events_router.message(AddEventFSM.link)
async def add_event_link(message: Message, state: FSMContext) -> None:
    link = None if message.text == "-" else message.text
    await state.update_data(link=link)
    await state.set_state(AddEventFSM.img)
    await message.answer("Отправьте ссылку на изображение (или '-' если нет):")
    logger.debug(f"Указана ссылка события: {link}")


@admin_events_router.message(AddEventFSM.img)
async def add_event_img(message: Message, state: FSMContext, session: AsyncSession) -> None:
    img = None if message.text == "-" else message.text
    await state.update_data(img=img)
    data = await state.get_data()

    await orm_add_event(session, data)
    await state.set_state(AddEventFSM.notify)

    logger.info(f"Добавлено событие: {data['name']} ({data['date']})")
    await message.answer(
        f"✅ Событие '{data['name']}' добавлено!\n\n"
        "Хотите оповестить пользователей? (Да/Нет)"
    )


@admin_events_router.message(AddEventFSM.notify)
async def add_event_notify(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    notify = message.text.lower() in {"yes", "да", "1"}
    data = await state.get_data()

    if notify:
        await notify_subscribers(
            bot,
            session,
            f"📰 Новое мероприятие: {data['name']} \n\n{data['date']}",
            data["img"],
            type_="events",
        )
        await message.answer("👍 Пользователи оповещены.", reply_markup=get_admin_events_kb())
        logger.info(f"Оповещены пользователи о новом событии: {data['name']}")
    else:
        await message.answer("👍 Событие добавлено без оповещения.", reply_markup=get_admin_events_kb())
        logger.info(f"Событие {data['name']} добавлено без оповещения")
    await state.clear()


# ================== РЕДАКТИРОВАНИЕ СОБЫТИЯ ==================
@admin_events_router.callback_query(F.data == "edit_event")
async def edit_event_start(callback: CallbackQuery, session: AsyncSession) -> None:
    events = await orm_get_events(session)
    if not events:
        await callback.message.answer("❌ Нет событий для изменения.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=e.name, callback_data=f"edit_event_{e.id}")]
            for e in events
        ]
    )
    await callback.message.answer("Выберите событие:", reply_markup=kb)
    logger.debug("Админ открыл список для редактирования событий")


@admin_events_router.callback_query(F.data.startswith("edit_event_"))
async def edit_event_choose(callback: CallbackQuery, state: FSMContext) -> None:
    event_id = int(callback.data.split("_")[2])
    await state.update_data(id=event_id)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Название", callback_data="field_name")],
            [InlineKeyboardButton(text="Мероприятие бесплатное? (да/нет)", callback_data="field_is_free")],
            [InlineKeyboardButton(text="Дата", callback_data="field_date")],
            [InlineKeyboardButton(text="Описание", callback_data="field_description")],
            [InlineKeyboardButton(text="Ссылка", callback_data="field_link")],
            [InlineKeyboardButton(text="Изображение", callback_data="field_img")],
        ]
    )
    await state.set_state(EditEventFSM.field)
    await callback.message.answer("Выберите поле для изменения:", reply_markup=kb)
    logger.debug(f"Админ выбрал событие для редактирования: id={event_id}")


@admin_events_router.callback_query(F.data.startswith("field_"), EditEventFSM.field)
async def edit_event_field(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.replace("field_", "")
    await state.update_data(field=field)
    await state.set_state(EditEventFSM.value)
    await callback.message.answer(f"Введите новое значение для поля {field}:")
    logger.debug(f"Редактируется поле события: {field}")


@admin_events_router.message(EditEventFSM.value)
async def edit_event_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    field, value = data["field"], message.text

    if field == "date":
        try:
            value = datetime.strptime(value, "%Y-%m-%d %H:%M")
        except ValueError:
            await message.answer("❌ Формат даты: 2025-08-21 18:30")
            return
    if field == "is_free":
        value = value.lower() in ["да", "yes", 1]

    await orm_update_event(session, data["id"], {field: value})
    await state.clear()
    await message.answer("✅ Событие изменено!", reply_markup=get_admin_events_kb())
    logger.info(f"Событие id={data['id']} изменено (поле {field}) user_id={message.from_user.id}")


# ================== УДАЛЕНИЕ СОБЫТИЯ ==================
@admin_events_router.callback_query(F.data == "delete_event")
async def delete_event_start(callback: CallbackQuery, session: AsyncSession) -> None:
    events = await orm_get_events(session)
    if not events:
        await callback.message.answer("❌ Нет событий для удаления.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=e.name, callback_data=f"delete_event_{e.id}")]
            for e in events
        ]
    )
    await callback.message.answer("Выберите событие:", reply_markup=kb)
    logger.debug(f"Админ открыл список для удаления событий user_id ={callback.from_user.id}")


@admin_events_router.callback_query(F.data.startswith("delete_event_"))
async def delete_event_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    event_id = int(callback.data.split("_")[2])
    await orm_delete_event(session, event_id)
    await callback.message.answer("🗑 Событие удалено!", reply_markup=get_admin_events_kb())
    logger.warning(f"Событие удалено: id={event_id} user_id{callback.from_user.id}")


# ================== ОБНОВЛЕНИЕ ВСЕХ СОБЫТИЙ ==================
@admin_events_router.callback_query(F.data == "update_all_events")
async def update_all_events_prompt(callback: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="С оповещением", callback_data="update_all_events_True")],
            [InlineKeyboardButton(text="Без оповещения", callback_data="update_all_events_False")],
            [InlineKeyboardButton(text="Назад", callback_data="edit_events_panel")],
        ]
    )
    await callback.message.answer("Оповестить пользователей?", reply_markup=kb)


@admin_events_router.callback_query(F.data.startswith("update_all_events_"))
async def update_all_events_handler(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    update = callback.data.endswith("True")

    await callback.message.answer(
        "🔄 Запускаю обновление афиши...\n"
        "Примерное время: 2–3 минуты"
    )

    try:
        data, log_text = await asyncio.to_thread(update_all_events)
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка парсера: {e}")
        logger.error(f"Ошибка обновления афиши: {e}", exc_info=True)
        return

    updated, added = 0, 0

    for name, values in data.items():
        try:
            event_date, description, age_limits, img, link, is_free = values
        except ValueError:
            await callback.message.answer(f"⚠ Ошибка формата данных: {name}")
            logger.error(f"Некорректные данные события: {name}")
            continue

        event = await orm_query.orm_get_event_by_name(session, name)
        if event:
            await orm_update_event(session, event.id, {
                "date": datetime.strptime(event_date, "%Y-%m-%d %H:%M"),
                "description": description,
                "age_limits": age_limits,
                "img": img,
                "link": link,
                "is_free": is_free
            })
            updated += 1
        else:
            await orm_add_event(session, {
                "name": name,
                "date": datetime.strptime(event_date, "%Y-%m-%d %H:%M"),
                "description": description,
                "age_limits": age_limits,
                "img": img,
                "link": link,
                "is_free": is_free
            })
            added += 1

            if update:
                text = f"{name.capitalize()} | +{age_limits}\n\n{event_date}"
                await notify_subscribers(
                    bot, session,
                    f"📰 Обновление в афише! \n\n{text}",
                    img,
                    type_="events",
                )
                logger.info(f"Пользователи оповещены о новом событии: {name}")

    await callback.message.answer(
        f"{log_text}\n\n"
        f"🔄 Обновлено: {updated}\n"
        f"➕ Добавлено: {added}",
        reply_markup=get_admin_events_kb(),
    )
    logger.info(f"Обновление афиши завершено: обновлено={updated}, добавлено={added}")