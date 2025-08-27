from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
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


def get_studio_detail_keyboard(studio: Studios, page: int, photo_msg_id: int = 0):
    """Клавиатура для подробной карточки"""
    buttons = [
        [InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=f"studio_back:{studio.id}:{page}:{photo_msg_id}"
        )],
        [InlineKeyboardButton(text="🔗 Перейти на сайт", url="https://дк-яуза.рф/studii/")],
        [InlineKeyboardButton(text="🖍 Записаться в кружок", url="https://dk.mosreg.ru/")]
    ]
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


# --- Краткая карточка ---
async def render_studio_card(callback: CallbackQuery, studio: Studios, page: int):
    description = studio.description or "Нет описания"
    short_desc = description[:350] + ("<i>… \n\nнажмите на <b>\"Подробнее\"</b> чтобы посмотреть больше и записаться</i>" if len(description) > 350 else "")

    text = f"<b>{studio.name}</b>\n\n{short_desc}"
    text = (
        f"<b>{studio.name}</b>\n\n"
        f"👨‍🏫 Преподаватель: {studio.teacher or '—'}\n"
        f"💰 Стоимость: {studio.cost} руб.\n"
        f"🎂 Возраст: {studio.age}\n"
        f"🏷 Категория: {studio.category if studio.category != 'unknown' else 'Другое'}\n"
        # f"⏱ Обновлено: {studio.updated}\n\n"
        f"ℹ️ {short_desc or 'Нет описания'}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"studios_page:{page}")],
        [InlineKeyboardButton(text="ℹ Подробнее", callback_data=f"studio_detail:{studio.id}:{page}")]
    ])

    # Удаляем список
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Новая карточка с фото
    if studio.img:
        await callback.message.answer_photo(studio.img, caption=text[:1024], reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.answer(text[:4095], reply_markup=kb, parse_mode="HTML")

    await callback.answer()


# --- Детальная карточка ---
async def render_studio_detail(callback: CallbackQuery, studio: Studios, page: int):
    text = (
        f"<b>{studio.name}</b>\n\n"
        f"👨‍🏫 Преподаватель: {studio.teacher or '—'}\n"
        f"💰 Стоимость: {studio.cost} руб.\n"
        f"🎂 Возраст: {studio.age}\n"
        f"🏷 Категория: {studio.category}\n"
        # f"⏱ Обновлено: {studio.updated}\n\n"
        f"ℹ️ {studio.description or 'Нет описания'}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"studio_card:{studio.id}:{page}")],
        [InlineKeyboardButton(text="🔗 Перейти на сайт", url="https://дк-яуза.рф/studii/")],
        [InlineKeyboardButton(text="🖍 Записаться в кружок", url="https://dk.mosreg.ru/")]
    ])

    # Редактируем текущее сообщение (меняем фото/текст на детальное описание)
    try:
        if callback.message.photo:
            await callback.message.delete()  # если было фото, удаляем
            await callback.message.answer(text[:4095], reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(text[:4095], reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text[:4095], reply_markup=kb, parse_mode="HTML")

    await callback.answer()



# --- Назад из детальной к краткой ---
# @studios_router.callback_query(F.data.startswith("studio_back_card:"))
# async def back_to_card(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
#     data = await state.get_data()
#     studio_id, page = map(int, callback.data.split(":")[1:])
#     studio = await orm_get_studio(session, studio_id)
#
#     # Удаляем все detail-сообщения
#     for msg_id in data.get("detail_msg_ids", []):
#         try:
#             await callback.bot.delete_message(callback.message.chat.id, msg_id)
#         except Exception:
#             pass
#
#     await render_studio_card(callback, studio, page, state)


# --- Назад из карточки в список ---
@studios_router.callback_query(F.data.startswith("studios_page:"))
async def back_to_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    card_msg_id = data.get("card_msg_id")
    if card_msg_id:
        try:
            await callback.bot.delete_message(callback.message.chat.id, card_msg_id)
        except Exception:
            pass
    page = int(callback.data.split(":")[1])
    await render_studio_list(callback, session, page)


# ---------- Хендлеры ----------
@studios_router.callback_query(F.data == "list_studios")
async def list_studios_handler(callback: CallbackQuery, session: AsyncSession):
    await render_studio_list(callback, session, page=1)


@studios_router.callback_query(F.data.startswith("studios_page:"))
async def studios_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await render_studio_list(callback, session, page)


from aiogram.fsm.context import FSMContext

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


@studios_router.callback_query(F.data.startswith("studio_back:"))
async def studio_back_handler(callback: CallbackQuery, session: AsyncSession):
    studio_id, page, photo_msg_id = map(int, callback.data.split(":")[1:])

    # 🗑 удаляем фото (если оно было)
    if photo_msg_id:
        try:
            await callback.bot.delete_message(callback.message.chat.id, photo_msg_id)
        except Exception:
            pass

    studio = await orm_get_studio(session, studio_id)
    if studio:
        await render_studio_card(callback, studio, page)
    else:
        await callback.answer("Студия не найдена", show_alert=True)
