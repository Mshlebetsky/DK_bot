import asyncio

from aiogram import Router, F, types, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import or_f,Command

from sqlalchemy.ext.asyncio import AsyncSession

from database import orm_query
from database.orm_query import (
    orm_add_news, orm_update_news, orm_delete_news,
    orm_get_all_news
)
from handlers.notification import notify_subscribers
from logic.scrap_news import update_all_news
from filter.filter import IsAdmin, ChatTypeFilter, IsSuperAdmin, IsEditor

admin_news_router = Router()
admin_news_router.message.filter(or_f(IsSuperAdmin(),IsEditor()))


# --- FSM ---
class AddNewsFSM(StatesGroup):
    name = State()
    description = State()
    img = State()
    notify = State()
class EditNewsFSM(StatesGroup):
    id = State()
    field = State()
    value = State()


# --- Клавиатуры ---
def get_admin_news_kb():
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить новость", callback_data="add_news")],
        [InlineKeyboardButton(text="✏️ Изменить новость", callback_data="edit_news")],
        [InlineKeyboardButton(text="🗑 Удалить новость", callback_data="delete_news")],
        [InlineKeyboardButton(text="📋 Список новостей", callback_data="list_news")],
        [InlineKeyboardButton(text="🔄 Обновить все новости", callback_data="update_all_news")],
        [InlineKeyboardButton(text="🛠В панель администратора", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Стартовое меню ---
@admin_news_router.message(Command('edit_news'))
async def admin_news_menu(message: Message):
    await message.answer("Меню управления новостями:", reply_markup=get_admin_news_kb())

@admin_news_router.callback_query(F.data == 'edit_news_panel')
async def admin_events_menu(callback: CallbackQuery):
    await callback.message.edit_text("Меню управления новостями:", reply_markup=get_admin_news_kb())

# --- Добавление новости ---
@admin_news_router.callback_query(F.data == "add_news")
async def add_news_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddNewsFSM.name)
    await callback.message.answer("Введите название новости:")

@admin_news_router.message(AddNewsFSM.name)
async def add_news_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddNewsFSM.description)
    await message.answer("Введите описание новости:")

@admin_news_router.message(AddNewsFSM.description)
async def add_news_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddNewsFSM.img)
    await message.answer("Отправьте ссылку на изображение (или '-' если нет):")

@admin_news_router.message(AddNewsFSM.img)
async def add_news_img(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    img = None if message.text == "-" else message.text
    await state.update_data(img=img)
    data = await state.get_data()
    await orm_add_news(session, data)
    await state.set_state(AddNewsFSM.notify)
    await message.answer(f"✅ Событие добавлено!\n\nХотите оповестить об этом пользователей?(Да/нет)")

@admin_news_router.message(AddNewsFSM.notify)
async def add_news_anounse(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    anouncement = True if message.text.lower() in ['yes', 'да', 1] else False
    if anouncement:
        data = await state.get_data()
        text = f"📰 Новая новость!\n\n<b>{data['name']}</b>\n\n{data['description'][:300]}..."
        await notify_subscribers(bot, session, f"📰 Обновление в новостях! \n\n{text}", data['img'], type_="news")
        await message.answer('👍Уведомление пользователям успешно отправлено', reply_markup=get_admin_news_kb())
    else:
        await message.answer('👍Новость успешно добавлено без оповещения пользователей', reply_markup=get_admin_news_kb())
    await state.clear()


# --- Изменение новости ---
@admin_news_router.callback_query(F.data == "edit_news")
async def edit_news_start(callback: CallbackQuery, session: AsyncSession):
    news = await orm_get_all_news(session)
    if not news:
        await callback.message.answer("❌ Нет новостей для изменения.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=n.name, callback_data=f"edit_news_{n.id}")] for n in news
    ])
    await callback.message.answer("Выберите новость:", reply_markup=kb)

@admin_news_router.callback_query(F.data.startswith("edit_news_"))
async def edit_news_choose(callback: CallbackQuery, state: FSMContext):
    news_id = int(callback.data.split("_")[2])
    await state.update_data(id=news_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data="field_name")],
        [InlineKeyboardButton(text="Описание", callback_data="field_description")],
        [InlineKeyboardButton(text="Изображение", callback_data="field_img")],
    ])
    await state.set_state(EditNewsFSM.field)
    await callback.message.answer("Выберите поле для изменения:", reply_markup=kb)

@admin_news_router.callback_query(F.data.startswith("field_"), EditNewsFSM.field)
async def edit_news_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("field_", "")
    await state.update_data(field=field)
    await state.set_state(EditNewsFSM.value)
    await callback.message.answer(f"Введите новое значение для поля {field}:")

@admin_news_router.message(EditNewsFSM.value)
async def edit_news_value(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await orm_update_news(session, data["id"], {data["field"]: message.text})
    await state.clear()
    await message.answer("✅ Новость изменена!", reply_markup=get_admin_news_kb())


# --- Удаление новости ---
@admin_news_router.callback_query(F.data == "delete_news")
async def delete_news_start(callback: CallbackQuery, session: AsyncSession):
    news = await orm_get_all_news(session)
    if not news:
        await callback.message.answer("❌ Нет новостей для удаления.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=n.name, callback_data=f"delete_news_{n.id}")] for n in news
    ])
    await callback.message.answer("Выберите новость:", reply_markup=kb)

@admin_news_router.callback_query(F.data.startswith("delete_news_"))
async def delete_news_confirm(callback: CallbackQuery, session: AsyncSession):
    news_id = int(callback.data.split("_")[2])
    await orm_delete_news(session, news_id)
    await callback.message.answer("🗑 Новость удалена!", reply_markup=get_admin_news_kb())



# --- Обновить все новости ---
@admin_news_router.callback_query(F.data == "update_all_news")
async def update_all_news_handler_(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    question_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="C оповещением пользователей", callback_data=f"update_all_news_True")],
        [InlineKeyboardButton(text="Без оповещения пользователей", callback_data=f"update_all_news_False")],
        [InlineKeyboardButton(text="Назад", callback_data=f"edit_news_panel")]

    ])
    await callback.message.answer("Оповестить пользователей?",  reply_markup=question_kb)
@admin_news_router.callback_query(F.data.startswith("update_all_news_"))
async def update_all_news_handler(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    try:
        update = (callback.data.split('_')[3] == str(True))
    except:
        update = False
    await callback.message.answer("🔄 Запускаю обновление новостей, пожалуйста подождите...\nПримерное время обновления ~1 минута")
    try:
        data, log_text = await asyncio.to_thread(update_all_news)
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка парсера: {e}")
        return

    updated, added = 0, 0
    for name, values in data.items():
        try:
            description, img = values
        except ValueError:
            await callback.message.answer(f"⚠ Ошибка формата данных: {name}")
            continue

        news = await orm_query.orm_get_news_by_name(session, name)
        if news:
            await orm_update_news(session, news.id, {
                "description": description,
                "img": img,
            })
            updated += 1
        else:
            await orm_add_news(session, {
                "name": name,
                "description": description,
                "img": img,
            })
            added += 1
            if update:
                text = f"{name.capitalize()}"
                await notify_subscribers(bot, session, f"📰 Обновление в новостях! \n\n{text}", img, type_="news")
    await callback.message.answer(
        f"{log_text}\n\n"
        f"🔄 Обновлено: {updated}\n"
        f"➕ Добавлено: {added}",
        reply_markup=get_admin_news_kb()
    )