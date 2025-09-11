import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import Studios
from database.orm_query import orm_get_studio
from logic.helper import Big_litter_start

# ================== ЛОГИРОВАНИЕ ==================

logger = logging.getLogger(__name__)

# ================== РОУТЕР ==================


studios_router = Router()


STUDIOS_PER_PAGE = 8


# ---------- Клавиатуры ----------
def get_studios_keyboard(studios, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """
    Генерация клавиатуры списка студий.
    """
    keyboard = [
        [InlineKeyboardButton(
            text=f"{'🆓' if studio.cost == 0 else '💳'} {Big_litter_start(studio.name)}",
            callback_data=f"studio_card:{studio.id}:{page}"
        )]
        for studio in studios
    ]

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⏮ Назад", callback_data=f"studios_page:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="⏭ Далее", callback_data=f"studios_page:{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)
        keyboard.append([InlineKeyboardButton(text="🏠 В Главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_studio_card_keyboard(studio_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"studios_page:{page}")],
        [InlineKeyboardButton(text="ℹ Подробнее", callback_data=f"studio_detail:{studio_id}:{page}")],
    ])


def get_studio_detail_keyboard(studio: Studios, page: int, photo_msg_id: int = 0) -> InlineKeyboardMarkup:
    """
    Клавиатура для детальной карточки студии.
    """
    buttons = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"studio_back:{studio.id}:{page}:{photo_msg_id}")],
        [InlineKeyboardButton(text="🔗 Перейти на сайт", url="https://дк-яуза.рф/studii/")],
        [InlineKeyboardButton(text="🖍 Записаться в кружок", url="https://dk.mosreg.ru/")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------- Рендеры ----------
async def render_studio_list(message_or_callback, session: AsyncSession, page: int = 1) -> None:
    """
    Отображение списка студий.
    """

    offset = (page - 1) * STUDIOS_PER_PAGE
    studios = (
        await session.execute(
            select(Studios).offset(offset).limit(STUDIOS_PER_PAGE)
        )
    ).scalars().all()

    total = (await session.execute(select(func.count(Studios.id)))).scalar_one()
    total_pages = (total + STUDIOS_PER_PAGE - 1) // STUDIOS_PER_PAGE

    if not studios:
        logger.warning("Страница %s пуста — студии не найдены", page)
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.delete()
            await message_or_callback.message.answer("❌ Студии не найдены")
        else:
            await message_or_callback.answer("❌ Студии не найдены")
        return

    text = "📋 <b>Список студий:</b>\n\n"
    keyboard = get_studios_keyboard(studios, page, total_pages)
    target = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

    try:
        if target.text:
            await target.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await target.delete()
            await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error("Ошибка при отображении списка студий: %s", e, exc_info=True)
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.answer()


async def render_studio_card(callback: CallbackQuery, studio: Studios, page: int) -> None:
    """
    Краткая карточка студии.
    """
    logger.info(f"Пользователь {callback.from_user.id} просматривает студию {studio.id}")

    description = studio.description or "Нет описания"
    short_desc = description[:350] + (
        "<i>… \n\nнажмите на <b>\"Подробнее\"</b> чтобы посмотреть больше и записаться</i>"
        if len(description) > 350 else ""
    )

    text = (
        f"<b>{studio.name}</b>\n\n"
        f"👨‍🏫 Преподаватель: {studio.teacher or '—'}\n"
        f"💰 Стоимость: {studio.cost} руб.\n"
        f"🎂 Возраст: {studio.age}\n"
        f"🏷 Категория: {studio.category if studio.category != 'unknown' else 'Другое'}\n"
        f"ℹ️ {short_desc or 'Нет описания'}"
    )
    kb = get_studio_card_keyboard(studio.id, page)

    try:
        await callback.message.delete()
    except Exception as e:
        logger.debug("Не удалось удалить предыдущее сообщение: %s", e)

    try:
        if studio.img:
            await callback.message.answer_photo(studio.img, caption=text[:1024], reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.answer(text[:4095], reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error("Ошибка при показе карточки студии ID=%s: %s", studio.id, e, exc_info=True)

    await callback.answer()


async def render_studio_detail(callback: CallbackQuery, studio: Studios, page: int) -> None:
    """
    Полная карточка студии.
    """
    logger.debug("Открытие детальной карточки студии. ID=%s, Страница=%s", studio.id, page)

    text = (
        f"<b>{studio.name}</b>\n\n"
        f"👨‍🏫 Преподаватель: {studio.teacher or '—'}\n"
        f"💰 Стоимость: {studio.cost} руб.\n"
        f"🎂 Возраст: {studio.age}\n"
        f"🏷 Категория: {studio.category}\n"
        f"ℹ️ {studio.description or 'Нет описания'}"
    )
    kb = get_studio_detail_keyboard(studio, page)

    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text[:4095], reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(text[:4095], reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error("Ошибка при показе детальной карточки студии ID=%s: %s", studio.id, e, exc_info=True)
        await callback.message.answer(text[:4095], reply_markup=kb, parse_mode="HTML")

    await callback.answer()


# ---------- Хендлеры ----------
@studios_router.callback_query(F.data == "list_studios")
async def list_studios_handler(callback: CallbackQuery, session: AsyncSession):
    logger.info("Пользователь %s запросил список студий", callback.from_user.id)
    await render_studio_list(callback, session, page=1)


@studios_router.callback_query(F.data.startswith("studios_page:"))
async def studios_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    logger.info("Пользователь %s переключился на страницу %s студий", callback.from_user.id, page)
    await render_studio_list(callback, session, page)


@studios_router.callback_query(F.data.startswith("studio_card:"))
async def studio_card_handler(callback: CallbackQuery, session: AsyncSession):
    studio_id, page = map(int, callback.data.split(":")[1:])
    logger.info("Пользователь %s открыл карточку студии ID=%s", callback.from_user.id, studio_id)

    studio = await orm_get_studio(session, studio_id)
    if not studio:
        logger.warning("Студия ID=%s не найдена", studio_id)
        await callback.answer("Студия не найдена", show_alert=True)
        return

    await render_studio_card(callback, studio, page)


@studios_router.callback_query(F.data.startswith("studio_detail:"))
async def studio_detail_handler(callback: CallbackQuery, session: AsyncSession):
    studio_id, page = map(int, callback.data.split(":")[1:])
    logger.info("Пользователь %s открыл детальную карточку студии ID=%s", callback.from_user.id, studio_id)

    studio = await orm_get_studio(session, studio_id)
    if not studio:
        logger.warning("Студия ID=%s не найдена", studio_id)
        await callback.answer("Студия не найдена", show_alert=True)
        return

    await render_studio_detail(callback, studio, page)


@studios_router.callback_query(F.data.startswith("studio_back:"))
async def studio_back_handler(callback: CallbackQuery, session: AsyncSession):
    studio_id, page, photo_msg_id = map(int, callback.data.split(":")[1:])
    logger.info("Пользователь %s вернулся из детальной карточки студии ID=%s на страницу %s", callback.from_user.id, studio_id, page)

    if photo_msg_id:
        try:
            await callback.bot.delete_message(callback.message.chat.id, photo_msg_id)
        except Exception as e:
            logger.debug("Не удалось удалить фото-сообщение ID=%s: %s", photo_msg_id, e)

    studio = await orm_get_studio(session, studio_id)
    if studio:
        await render_studio_card(callback, studio, page)
    else:
        logger.warning("Студия ID=%s не найдена при возврате", studio_id)
        await callback.answer("Студия не найдена", show_alert=True)
