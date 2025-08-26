from aiogram import Router, F, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import Studios
from database.orm_query import orm_get_studio


studios_router = Router()

STUDIOS_PER_PAGE = 8

# ---------- Клавиатуры ----------
def get_studios_keyboard(studios, page: int, total_pages: int):
    keyboard = [
        [InlineKeyboardButton(
            text=f"{'🆓' if studio.cost == 0 else '💳'} {studio.name.capitalize()}",
            callback_data=f"studio_card:{studio.id}:{page}"
        )]
        for studio in studios
    ]

    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⏮ Назад", callback_data=f"studios_page:{page-1}")
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="⏭ Далее", callback_data=f"studios_page:{page+1}")
        )
    if nav_buttons:
        keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_studio_card_keyboard(studio_id: int, page: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"studios_page:{page}")],
        [InlineKeyboardButton(text="ℹ Подробнее", callback_data=f"studio_detail:{studio_id}:{page}")]
    ])


def get_studio_detail_keyboard(studio: Studios, page: int):
    buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data=f"studio_card:{studio.id}:{page}")]]
    link = 'https://дк-яуза.рф/studii/'
    link2 = 'https://dk.mosreg.ru/'
    buttons.append([InlineKeyboardButton(text="🔗 Перейти на сайт", url=link)])
    buttons.append([InlineKeyboardButton(text="🖍 Записаться в кружок", url=link2)]
                   )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------- Универсальные функции ----------
async def render_studio_list(message_or_callback, session: AsyncSession, page: int = 1):
    """Показ списка студий"""
    offset = (page - 1) * STUDIOS_PER_PAGE
    studios = (
        await session.execute(
            select(Studios).offset(offset).limit(STUDIOS_PER_PAGE)
        )
    ).scalars().all()

    total = (await session.execute(select(func.count(Studios.id)))).scalar_one()
    total_pages = (total + STUDIOS_PER_PAGE - 1) // STUDIOS_PER_PAGE

    text = "📋 <b>Список студий:</b>\n\n"
    keyboard = get_studios_keyboard(studios, page, total_pages)

    target = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

    if not studios:
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.delete()  # удаляем старое сообщение, если оно есть
            await message_or_callback.message.answer("❌Студии не найдены")
        else:
            await message_or_callback.answer("❌Студии не найдены")
        return

    try:
        if target.text:
            await target.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await target.delete()
            await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.answer()


async def render_studio_card(message_or_callback, studio: Studios, page: int):
    """Карточка студии (краткая)"""
    description = studio.description or "Нет описания"
    short_desc = description[:500] + ("…" if len(description) > 500 else "")

    text = f"<b>{studio.name}</b>\n\n{short_desc}"
    kb = get_studio_card_keyboard(studio.id, page)

    target = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

    try:
        if studio.img:
            if target.photo:
                await target.edit_caption(caption=text[:1024], reply_markup=kb, parse_mode="HTML")
            else:
                await target.delete()
                await target.answer_photo(studio.img, caption=text[:1024], reply_markup=kb, parse_mode="HTML")
        else:
            if target.text:
                await target.edit_text(text[:4095], reply_markup=kb, parse_mode="HTML")
            else:
                await target.delete()
                await target.answer(text[:4095], reply_markup=kb, parse_mode="HTML")
    except Exception:
        await target.answer(text[:4095], reply_markup=kb, parse_mode="HTML")

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.answer()


async def render_studio_detail(message_or_callback, studio: Studios, page: int):
    """Полная карточка студии"""
    text = (
        f"<b>{studio.name}</b>\n\n"
        f"👨‍🏫 Преподаватель: {studio.teacher or '—'}\n"
        f"💰 Стоимость: {studio.cost} руб.\n"
        f"🎂 Возраст: {studio.age}\n"
        f"🏷 Категория: {studio.category}\n"
        f"⏱ Обновлено: {studio.updated}\n\n"
        f"ℹ️ {studio.description or 'Нет описания'}"
    )
    kb = get_studio_detail_keyboard(studio, page)

    target = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

    try:
        if studio.img:
            if target.photo:
                await target.edit_caption(caption=text[:1024], reply_markup=kb, parse_mode="HTML")
            else:
                await target.delete()
                await target.answer_photo(studio.img, caption=text[:1024], reply_markup=kb, parse_mode="HTML")
        else:
            if target.text:
                await target.edit_text(text[:4095], reply_markup=kb, parse_mode="HTML")
            else:
                await target.delete()
                await target.answer(text[:4095], reply_markup=kb, parse_mode="HTML")
    except Exception:
        await target.answer(text[:4095], reply_markup=kb, parse_mode="HTML")

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.answer()


# ---------- Хендлеры ----------
@studios_router.callback_query(F.data == "list_studios")
async def list_studios_handler(callback: CallbackQuery, session: AsyncSession):
    await render_studio_list(callback, session, page=1)


@studios_router.callback_query(F.data.startswith("studios_page:"))
async def studios_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await render_studio_list(callback, session, page)


@studios_router.callback_query(F.data.startswith("studio_card:"))
async def studio_card_handler(callback: CallbackQuery, session: AsyncSession):
    studio_id, page = map(int, callback.data.split(":")[1:])
    studio = await orm_get_studio(session, studio_id)
    if not studio:
        await callback.answer("Студия не найдена", show_alert=True)
        return
    await render_studio_card(callback, studio, page)


@studios_router.callback_query(F.data.startswith("studio_detail:"))
async def studio_detail_handler(callback: CallbackQuery, session: AsyncSession):
    studio_id, page = map(int, callback.data.split(":")[1:])
    studio = await orm_get_studio(session, studio_id)
    if not studio:
        await callback.answer("Студия не найдена", show_alert=True)
        return
    await render_studio_detail(callback, studio, page)
