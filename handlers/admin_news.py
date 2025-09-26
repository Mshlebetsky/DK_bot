import asyncio
import logging
from dataclasses import field

from aiogram import Router, F, types, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import or_f, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlalchemy.ext.asyncio import AsyncSession

from database import orm_query
from database.orm_query import (
    orm_add_news, orm_update_news, orm_delete_news,
    orm_get_all_news, orm_get_news
)
from handlers.notification import notify_subscribers
from logic.scrap_news import update_all_news
from filter.filter import IsSuperAdmin, IsEditor


# ================== ЛОГИРОВАНИЕ ==================

logger = logging.getLogger(__name__)

# ================== РОУТЕР ==================


admin_news_router = Router()
admin_news_router.message.filter(or_f(IsSuperAdmin(), IsEditor()))


# --- FSM ---
class AddNewsFSM(StatesGroup):
    title = State()
    description = State()
    img = State()
    notify = State()


class EditNewsFSM(StatesGroup):
    id = State()
    field = State()
    value = State()


# --- Keyboards ---
def get_admin_news_kb() -> InlineKeyboardMarkup:
    """Returns admin panel keyboard for managing news."""
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить новость", callback_data="add_news")],
        [InlineKeyboardButton(text="✏️ Изменить новость", callback_data="edit_news")],
        [InlineKeyboardButton(text="🗑 Удалить новость", callback_data="delete_news")],
        [InlineKeyboardButton(text="📋 Список новостей", callback_data="list_news")],
        [InlineKeyboardButton(text="🔄 Обновить все новости", callback_data="update_all_news")],
        [InlineKeyboardButton(text="🛠 В панель администратора", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


PER_PAGE = 10

def get_news_keyboard(news_list, page: int = 0):
    """Клавиатура для редактирования новостей по страницам."""
    news_list = sorted(news_list, key=lambda n: n.name.lower())
    builder = InlineKeyboardBuilder()
    start, end = page * PER_PAGE, page * PER_PAGE + PER_PAGE
    for n in news_list[start:end]:
        builder.button(text=n.name, callback_data=f"edit_news_{n.id}")
    builder.button(text="🛠В меню управления", callback_data="edit_news_panel")
    builder.adjust(1)
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"news_page_{page-1}")
    if end < len(news_list):
        builder.button(text="Вперёд ➡️", callback_data=f"news_page_{page+1}")
    return builder.as_markup()

def get_delete_news_keyboard(news_list, page: int = 0):
    """Клавиатура для удаления новостей по страницам."""
    news_list = sorted(news_list, key=lambda n: n.name.lower())
    builder = InlineKeyboardBuilder()
    start, end = page * PER_PAGE, page * PER_PAGE + PER_PAGE
    for n in news_list[start:end]:
        # используем явный префикс delete_news_item_ чтобы не конфликтовать с pagination
        builder.button(text=f"🗑 {n.name}", callback_data=f"delete_news_item_{n.id}")
    builder.button(text="В меню управления", callback_data="edit_news_panel")
    builder.adjust(1)
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"delete_news_page_{page-1}")
    if end < len(news_list):
        builder.button(text="Вперёд ➡️", callback_data=f"delete_news_page_{page+1}")
    return builder.as_markup()


# --- Start Menu ---
@admin_news_router.message(Command("edit_news"))
async def admin_news_menu(message: Message):
    logger.info(f"Переход в меню управления новостями{message.from_user.id}")
    await message.answer("Меню управления новостями:", reply_markup=get_admin_news_kb())


@admin_news_router.callback_query(F.data == "edit_news_panel")
async def admin_events_menu(callback: CallbackQuery):
    logger.info(f"Переход в меню управления новостями (user_id{callback.from_user.id})")
    await callback.message.edit_text("Меню управления новостями:", reply_markup=get_admin_news_kb())


# --- Add News ---
@admin_news_router.callback_query(F.data == "add_news")
async def add_news_start(callback: CallbackQuery, state: FSMContext):
    logger.info("Admin %s started adding news", callback.from_user.id)
    await state.set_state(AddNewsFSM.title)
    await callback.message.answer("Введите название новости:")


@admin_news_router.message(AddNewsFSM.title)
async def add_news_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    logger.debug("News title set: %s", message.text)
    await state.set_state(AddNewsFSM.description)
    await message.answer("Введите описание новости:")


@admin_news_router.message(AddNewsFSM.description)
async def add_news_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    logger.debug("News description set (len=%d)", len(message.text))
    await state.set_state(AddNewsFSM.img)
    await message.answer("Отправьте ссылку на изображение (или '-' если нет):")


@admin_news_router.message(AddNewsFSM.img)
async def add_news_img(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    img = None if message.text == "-" else message.text
    await state.update_data(img=img)
    data = await state.get_data()
    if not data.get("name"):
        data["name"] = data.get("title")
    await orm_add_news(session, data)
    logger.info("News added: %s", data["title"])

    await state.set_state(AddNewsFSM.notify)
    await message.answer("✅ Новость добавлена! Хотите оповестить пользователей? (Да/нет)")


@admin_news_router.message(AddNewsFSM.notify)
async def add_news_announce(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    notify = message.text.lower() in ["yes", "да", "1"]
    data = await state.get_data()

    if notify:
        text = f"\n<b>{data['title']}</b>\n\n{data['description'][:300]}..."
        await notify_subscribers(bot, session, f"📰 Обновление в новостях!\n\n{text}", data["img"], type_="news")
        logger.info("News notification sent for: %s", data["title"])
        await message.answer("👍 Уведомление пользователям успешно отправлено", reply_markup=get_admin_news_kb())
    else:
        logger.info("News added without notification: %s", data["title"])
        await message.answer("👍 Новость добавлена без оповещения пользователей", reply_markup=get_admin_news_kb())

    await state.clear()


# --- Edit News ---
@admin_news_router.callback_query(F.data == "edit_news")
async def edit_news_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    news_list = await orm_get_all_news(session)
    if not news_list:
        await callback.message.answer("❌ Нет новостей для изменения.")
        return
    await state.update_data(news=[{"id": n.id, "name": n.name} for n in news_list])
    kb = get_news_keyboard(news_list, page=0)
    await callback.message.answer("Выберите новость:", reply_markup=kb)


@admin_news_router.callback_query(F.data.startswith("news_page_"))
async def news_page(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    news_list = [type("Obj", (), n) for n in data["news"]]
    page = int(callback.data.split("_")[-1])
    kb = get_news_keyboard(news_list, page=page)
    await callback.message.edit_reply_markup(reply_markup=kb)



@admin_news_router.callback_query(F.data.startswith("edit_news_"))
async def edit_news_choose(callback: CallbackQuery, state: FSMContext):
    news_id = int(callback.data.split("_")[2])
    await state.update_data(id=news_id)
    logger.info("Admin %s chose news %d for editing", callback.from_user.id, news_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data="field_title")],
        [InlineKeyboardButton(text="Описание", callback_data="field_description")],
        [InlineKeyboardButton(text="Изображение", callback_data="field_img")],
        [InlineKeyboardButton(text="Запретить автоматическое изменение новости(да/нет)", callback_data="field_lock_changes")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"edit_news_panel")]
    ])
    await state.set_state(EditNewsFSM.field)
    await callback.message.answer("Выберите поле для изменения:", reply_markup=kb)


@admin_news_router.callback_query(F.data.startswith("field_"), EditNewsFSM.field)
async def edit_news_field(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    field = callback.data.replace("field_", "")
    await state.update_data(field=field)
    await state.set_state(EditNewsFSM.value)

    data = await state.get_data()
    news = await orm_get_news(session, data["id"])
    if field != 'title':
        current_value = getattr(news, field, None)
    else:
        if news.title == '':
            current_value = getattr(news, 'name', None)
        else:
            current_value = getattr(news, 'title', None)

    await callback.message.answer(f"Введите новое значение для поля {field}:\n"
                                  f"{'Введите - чтобы вернуть изначальное значение названия' if field == 'title' else ''}"
                                  f"\nЗначение сейчас:")
    await callback.message.answer(f"{current_value}")
    logger.debug("Выбранное поле для редактирования: %s", field)


@admin_news_router.message(EditNewsFSM.value)
async def edit_news_value(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    field, value, news_id = data["field"], message.text, data["id"]


    if message.text == "-":
        value = ''
    if field == "lock_changes":
        value = value.lower() in ["да", "yes", 1, "True"]

    try:
        await orm_update_news(session, news_id, {field: value})
        logger.info("Обновлено поле %s у новости id=%s", field, news_id)
        await message.answer("✅ Новость успешно изменена!", reply_markup=get_admin_news_kb())
    except Exception as e:
        logger.exception("Ошибка при обновлении студии id=%s: %s", news_id, e)
        await message.answer("❌ Ошибка при обновлении студии.")
    finally:
        await state.clear()


# --- Delete News ---
@admin_news_router.callback_query(F.data == "delete_news")
async def delete_news_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    news_list = await orm_get_all_news(session)
    if not news_list:
        await callback.message.answer("❌ Нет новостей для удаления.")
        return
    await state.update_data(delete_news=[{"id": n.id, "name": n.name} for n in news_list])
    kb = get_delete_news_keyboard(news_list, page=0)
    await callback.message.answer("Выберите новость для удаления:", reply_markup=kb)

@admin_news_router.callback_query(F.data.startswith("delete_news_page_"))
async def delete_news_page(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    news_list = [type("Obj", (), n) for n in data["delete_news"]]
    page = int(callback.data.split("_")[-1])
    kb = get_delete_news_keyboard(news_list, page=page)
    await callback.message.edit_reply_markup(reply_markup=kb)


@admin_news_router.callback_query(F.data.startswith("delete_news_item_"))
async def delete_news_confirm(callback: CallbackQuery, session: AsyncSession):
    try:
        news_id = int(callback.data.split("_")[-1])
    except (IndexError, ValueError):
        await callback.message.answer("❌ Неверный идентификатор новости.")
        return

    try:
        await orm_delete_news(session, news_id)
        logger.info("News %d deleted", news_id)
        await callback.message.answer("🗑 Новость удалена!", reply_markup=get_admin_news_kb())
    except Exception as e:
        logger.exception("Ошибка при удалении новости id=%s: %s", news_id, e)
        await callback.message.answer("❌ Ошибка при удалении новости.")



# --- Update All News ---
@admin_news_router.callback_query(F.data == "update_all_news")
async def update_all_news_handler_question(callback: CallbackQuery):
    question_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="С оповещением пользователей", callback_data="update_all_news_True")],
        [InlineKeyboardButton(text="Без оповещения пользователей", callback_data="update_all_news_False")],
        [InlineKeyboardButton(text="Назад", callback_data="edit_news_panel")],
    ])
    await callback.message.answer("Оповестить пользователей?", reply_markup=question_kb)


@admin_news_router.callback_query(F.data.startswith("update_all_news_"))
async def update_all_news_handler(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    notify_users = callback.data.endswith("True")
    logger.info("Admin %s started updating all news (notify=%s)", callback.from_user.id, notify_users)

    await callback.message.answer("🔄 Запускаю обновление новостей, пожалуйста подождите... (~1 минута)")

    try:
        data, log_text = await asyncio.to_thread(update_all_news)
    except Exception as e:
        logger.exception("News parser failed")
        await callback.message.answer(f"❌ Ошибка парсера: {e}")
        return

    updated, added = 0, 0
    for name, values in data.items():
        try:
            description, img = values
        except ValueError:
            logger.warning("Ошибка формата данных: %s", name)
            await callback.message.answer(f"⚠ Ошибка формата данных: {name}")
            continue

        news = await orm_query.orm_get_news_by_name(session, name)
        if news:
            if news.lock_changes == False:
                await orm_update_news(session, news.id, {"description": description, "img": img})
                updated += 1
        else:
            await orm_add_news(session, {"name": name, "description": description, "img": img})
            added += 1
            if notify_users:
                await notify_subscribers(bot, session, f"📰 Обновление в новостях!\n\n{name.capitalize()}", img, type_="news")

    logger.info("News update completed: updated=%d, added=%d", updated, added)
    await callback.message.answer(
        f"{log_text}\n\n🔄 Обновлено: {updated}\n➕ Добавлено: {added}",
        reply_markup=get_admin_news_kb()
    )