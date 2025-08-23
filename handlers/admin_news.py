from aiogram import Router, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import (
    orm_add_news, orm_get_news, orm_get_news_item,
    orm_update_news, orm_delete_news
)

admin_news_router = Router()


# FSM для добавления/редактирования
class NewsForm(StatesGroup):
    title = State()
    content = State()
    link = State()


# ➕ Добавить новость
@admin_news_router.message(F.text == "➕ Добавить новость")
async def add_news(message: types.Message, state: FSMContext):
    await state.set_state(NewsForm.title)
    await message.answer("Введите заголовок новости:")


@admin_news_router.message(NewsForm.title)
async def set_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(NewsForm.content)
    await message.answer("Введите текст новости:")


@admin_news_router.message(NewsForm.content)
async def set_content(message: types.Message, state: FSMContext):
    await state.update_data(content=message.text)
    await state.set_state(NewsForm.link)
    await message.answer("Введите ссылку на новость (или '-' если нет):")


@admin_news_router.message(NewsForm.link)
async def set_link(message: types.Message, state: FSMContext, session: AsyncSession):
    link = message.text if message.text != "-" else None
    await state.update_data(link=link)

    data = await state.get_data()
    await orm_add_news(session, data)
    await state.clear()

    text = (
        f"✅ Новость добавлена!\n\n"
        f"<b>{data['title']}</b>\n\n"
        f"{data['content']}\n"
        f"🔗 {data['link'] if data['link'] else '—'}"
    )
    await message.answer(text, parse_mode="HTML")


# 📰 Все новости
@admin_news_router.message(F.text == "📰 Все новости")
async def list_news(message: types.Message, session: AsyncSession):
    news = await orm_get_news(session)
    if not news:
        await message.answer("❌ Новостей пока нет")
        return

    text = "📰 <b>Новости:</b>\n\n"
    for n in news:
        text += f"ID: {n.id} | {n.title} ({n.created_at.strftime('%d.%m.%Y')})\n"

    await message.answer(text, parse_mode="HTML")


# 🔍 Подробнее
@admin_news_router.callback_query(F.data.startswith("news_detail:"))
async def news_detail(callback: types.CallbackQuery, session: AsyncSession):
    news_id = int(callback.data.split(":")[1])
    news_item = await orm_get_news_item(session, news_id)
    if not news_item:
        await callback.message.answer("❌ Новость не найдена")
        return

    text = (
        f"<b>{news_item.title}</b>\n\n"
        f"{news_item.content}\n\n"
        f"🕒 Опубликовано: {news_item.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )

    buttons = []
    if news_item.link:
        buttons.append([InlineKeyboardButton("🔗 Читать подробнее", url=news_item.link)])
    buttons.append([InlineKeyboardButton("❌ Удалить", callback_data=f"news_delete:{news_item.id}")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


# ❌ Удаление
@admin_news_router.callback_query(F.data.startswith("news_delete:"))
async def delete_news(callback: types.CallbackQuery, session: AsyncSession):
    news_id = int(callback.data.split(":")[1])
    await orm_delete_news(session, news_id)
    await callback.message.edit_text("✅ Новость удалена")
