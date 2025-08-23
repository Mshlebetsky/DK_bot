from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import News
from database import orm_query
from database.orm_query import (
    orm_add_news,
    orm_update_news,
    orm_delete_news,
    orm_get_news,
    orm_get_news_item,
    orm_get_news_by_name
)
from logic.scrap_news import update_all_news

admin_news_router = Router()

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

# --- Меню ---
@admin_news_router.message(F.text == "Редактировать Новости")
async def admin_news_menu(message: Message):
    await message.answer("Меню управления новостями:", reply_markup=get_admin_news_kb())

# --- Обновить все ---
@admin_news_router.callback_query(F.data == "update_all_news")
async def update_all_news_handler(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer("🔄 Запускаю обновление новостей, подождите...")

    try:
        data, log_text = update_all_news()
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при вызове парсера: {e}")
        return

    updated, added = 0, 0
    for name, values in data.items():
        try:
            description, img = values
        except ValueError:
            await callback.message.answer(f"⚠️ Пропущена новость {name}: неверный формат данных")
            continue

        news = await orm_get_news_by_name(session, name)
        if news:
            news.description = description
            news.img = img
            updated += 1
        else:
            new_news = News(
                name=name,
                description=description,
                img=img,
                is_shown=True
            )
            session.add(new_news)
            added += 1

    await session.commit()

    await callback.message.answer(
        f"{log_text}\n\n"
        f"🔄 Обновлено: {updated}\n"
        f"➕ Добавлено: {added}",
        reply_markup=get_admin_news_kb()
    )
