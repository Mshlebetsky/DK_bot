from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import orm_query
from database.models import News
from database.orm_query import (
    orm_add_news, orm_update_news, orm_delete_news,
    orm_get_news
)
from logic.scrap_news import update_all_news

admin_news_router = Router()

# --- FSM ---
class AddNewsFSM(StatesGroup):
    name = State()
    description = State()
    img = State()

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
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Стартовое меню ---
@admin_news_router.message(F.text == "Редактировать Новости")
async def admin_news_menu(message: Message):
    await message.answer("Меню управления новостями:", reply_markup=get_admin_news_kb())


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
async def add_news_img(message: Message, state: FSMContext, session: AsyncSession):
    img = None if message.text == "-" else message.text
    await state.update_data(img=img)
    data = await state.get_data()
    await orm_add_news(session, data)
    await state.clear()
    await message.answer("✅ Новость добавлена!", reply_markup=get_admin_news_kb())


# --- Изменение новости ---
@admin_news_router.callback_query(F.data == "edit_news")
async def edit_news_start(callback: CallbackQuery, session: AsyncSession):
    news = await orm_get_news(session)
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
    news = await orm_get_news(session)
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


# --- Список новостей ---
NEWS_PER_PAGE = 8

def get_news_keyboard(news, page: int, total_pages: int):
    keyboard = [
        [InlineKeyboardButton(text=n.name[:30], callback_data=f"news_card:{n.id}:{page}")]
        for n in news
    ]
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⏮ Назад", callback_data=f"news_page:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="⏭ Далее", callback_data=f"news_page:{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def list_news(message_or_callback, session: AsyncSession, page: int = 1):
    offset = (page - 1) * NEWS_PER_PAGE
    news = (
        await session.execute(
            select(News).offset(offset).limit(NEWS_PER_PAGE).order_by(News.id.desc())
        )
    ).scalars().all()

    total = (await session.execute(select(func.count(News.id)))).scalar_one()
    total_pages = (total + NEWS_PER_PAGE - 1) // NEWS_PER_PAGE

    if not news:
        target = message_or_callback.message if isinstance(message_or_callback, types.CallbackQuery) else message_or_callback
        await target.answer("Новости не найдены")
        if isinstance(message_or_callback, types.CallbackQuery):
            await message_or_callback.answer()
        return

    text = "<b>📋 Список новостей:</b>\n\n"
    kb = get_news_keyboard(news, page, total_pages)

    if isinstance(message_or_callback, types.CallbackQuery):
        msg = message_or_callback.message
        try:
            await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await msg.answer(text, reply_markup=kb)
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(text, reply_markup=kb)


# --- Хендлеры для списка ---
@admin_news_router.message(F.text.in_({"📋 Список новостей", "Список новостей"}))
async def news_list_command(message: types.Message, session: AsyncSession):
    await list_news(message, session, page=1)

@admin_news_router.callback_query(F.data.in_({"list_news", "news_list"}))
async def news_list_callback(callback: types.CallbackQuery, session: AsyncSession):
    await list_news(callback, session, page=1)

@admin_news_router.callback_query(F.data.startswith("news_page:"))
async def news_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await list_news(callback, session, page)


# карточка новости
@admin_news_router.callback_query(F.data.startswith("news_card:"))
async def news_card_handler(callback: CallbackQuery, session: AsyncSession):
    _, news_id, page = callback.data.split(":")
    news = await session.get(News, int(news_id))
    if not news:
        await callback.answer("Новость не найдена", show_alert=True)
        return

    desc = news.description or "Нет описания"
    short_desc = (desc[:500] + "…") if len(desc) > 500 else desc
    text = f"<b>{news.name}</b>\n\n{short_desc}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"news_page:{page}")],
        [InlineKeyboardButton(text="ℹ️ Подробнее", callback_data=f"news_detail:{news.id}")]
    ])

    try:
        await callback.message.delete()
    except Exception:
        pass

    if getattr(news, "img", None):
        await callback.message.answer_photo(news.img, caption=text, reply_markup=kb)
    else:
        await callback.message.answer(text, reply_markup=kb)

    await callback.answer()


# полная карточка
@admin_news_router.callback_query(F.data.startswith("news_detail:"))
async def news_detail_handler(callback: CallbackQuery, session: AsyncSession):
    news_id = int(callback.data.split(":")[1])
    news = await session.get(News, news_id)
    if not news:
        await callback.answer("Новость не найдена", show_alert=True)
        return

    text = f"<b>{news.name}</b>\n\n{news.description}"

    kb = [[InlineKeyboardButton(text="🔙 Назад к списку", callback_data="news_page:1")]]

    if news.img:
        try:
            await callback.message.answer_photo(news.img, caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        except Exception:
            await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    await callback.answer()


# --- Обновить все новости ---
@admin_news_router.callback_query(F.data == "update_all_news")
async def update_all_news_handler(callback: CallbackQuery, session: AsyncSession):
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

    await callback.message.answer(
        f"{log_text}\n\n"
        f"🔄 Обновлено: {updated}\n"
        f"➕ Добавлено: {added}",
        reply_markup=get_admin_news_kb()
    )
