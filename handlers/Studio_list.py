import hashlib
import logging

from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import Studios
from database.orm_query import orm_get_studio
from logic.helper import Big_litter_start


logger = logging.getLogger(__name__)
studios_router = Router()


STUDIOS_PER_PAGE = 8
CATEGORY_MAP: dict[str, str] = {}


# ---------- Вспомогательные функции ----------


def short_code(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:6]


# --------- Рендеры списка/краткой и подробной карточек студий


async def render_studio_list(callback: CallbackQuery, session: AsyncSession,
                              is_free: bool, category: str | None, page: int = 1):
    """
    Отображение списка студий с учётом фильтра "бесплатные / платные".
    """
    # await callback.message.answer(f"render func {category}")
    offset = (page - 1) * STUDIOS_PER_PAGE

    # корректная фильтрация: бесплатные — cost == 0, платные — cost > 0
    if is_free:
        cost_filter = (Studios.cost == 0)
    else:
        cost_filter = (Studios.cost > 0)

    # базовый запрос
    query = select(Studios).where(cost_filter)

    if category:
        query = query.where(Studios.category == category)


    studios = (await session.execute(query.offset(offset).limit(STUDIOS_PER_PAGE))).scalars().all()

    total_query = select(func.count(Studios.id)).where(cost_filter)
    if category:
        total_query = total_query.where(Studios.category == category)
        total = (await session.execute(total_query)).scalar_one()
    else:
        total = (await session.execute(total_query)).scalar_one()

    total_pages = (total + STUDIOS_PER_PAGE - 1) // STUDIOS_PER_PAGE

    if not studios:
        kb_back = InlineKeyboardMarkup(inline_keyboard=([[InlineKeyboardButton(text="⬅ К категориям", callback_data=f"studios_free_{is_free}")]]))
        await callback.message.answer("В этой категории пока нет студий", reply_markup=kb_back)
        await callback.answer()
        return

    text = f"📋 <b>Список {'бесплатных' if is_free else 'платных'} студий</b>\n"
    if category:
        text += f"Категория: {category.capitalize()}\n\n"

    # список кнопок
    keyboard = [
        [InlineKeyboardButton(
            text=f"{'🆓' if studio.cost == 0 else '💳'} {(Big_litter_start(studio.name) if studio.title == '' else studio.title)}",
            callback_data=f"studio_card:{studio.id}:{page}_{callback.data}"
        )] for studio in studios
    ]

    # пагинация
    query = callback.data.split(":")[-1]
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⏮ Назад", callback_data=f"std_p:{page - 1}:{query}"))
        logger.debug(callback.data)
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="⏭ Далее", callback_data=f"std_p:{page + 1}:{query}"))
        logger.debug(callback.data)
    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton(text="⬅ К категориям", callback_data=f"studios_free_{is_free}")])
    keyboard.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")])

    std_list_kb = InlineKeyboardMarkup(inline_keyboard=keyboard)

    if category != None:
        logger.info(f"{callback.data}")
        try:
            await callback.message.edit_text(
                f"📋 {'Бесплатные' if is_free else 'Платные'} студии в категории <b>{category.capitalize() if category != 'unknown' else 'Другое'}</b>:",
                reply_markup=std_list_kb
            )
        except:
            await callback.message.answer(
                f"📋 {'Бесплатные' if is_free else 'Платные'} студии в категории <b>{category.capitalize() if category != 'unknown' else 'Другое'}</b>:",
                reply_markup=std_list_kb
            )
    else:
        try:
            await callback.message.edit_text(
                f"📋 Список всех <b>{'бесплатных' if is_free else 'платных'}</b> студий:", reply_markup=std_list_kb
            )
        except:
            await callback.message.answer(
                f"📋 Список всех <b>{'бесплатных' if is_free else 'платных'}</b> студий:", reply_markup=std_list_kb
            )
        logger.info(f"{callback.data}")
    logger.info(
        "Пользователь %s открыл список студий категории %s",
        callback.from_user.id,
        category,
    )
    await callback.answer()



async def render_studio_card(callback: CallbackQuery, studio, session: AsyncSession, data):
    description = studio.description or "Нет описания"
    short_desc = description[:350] + (
        "<i>… \n\nнажмите на <b>\"Подробнее\"</b> чтобы посмотреть больше и записаться</i>" if len(
            description) > 350 else "")

    text = f"<b>{studio.name if studio.title == '' else studio.title}</b>\n\n{short_desc}"
    text = (
        f"<b>{studio.name if studio.title == '' else studio.title}</b>\n\n"
        f"👨‍🏫 Преподаватель: {studio.teacher or '—'}\n"
        f"💰 Стоимость: {studio.cost} руб.\n"
        f"🎂 Возраст: {studio.age}\n"
        f"🏷 Категория: {studio.category if studio.category != 'unknown' else 'Другое'}\n"
        f"ℹ️ {short_desc or 'Нет описания'}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"{data[0]}")],
        [InlineKeyboardButton(text="ℹ Подробнее", callback_data=f"std_dl:{studio.id}:{data[0]}")]
    ])


    if studio.img:
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer_photo(studio.img, caption=f"{text}", reply_markup=kb)
    else:
        await callback.message.answer(text[:4095], reply_markup=kb, parse_mode="HTML")


async def render_studio_detail(callback: CallbackQuery, session: AsyncSession, studio, query):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"{query}")],
        [InlineKeyboardButton(text="🔗 Перейти на сайт", url="https://дк-яуза.рф/studii/")],
        [InlineKeyboardButton(text="Расписание кружков (студий)", url="https://дк-яуза.рф/upload/rasp.docx")],
        [InlineKeyboardButton(text="🖍 Записаться в кружок", url="https://dk.mosreg.ru/")]
    ])

    text = (
        f"<b>{studio.name if studio.title == '' else studio.title}</b>\n\n"
        f"👨‍🏫 Преподаватель: {studio.teacher or '—'}\n"
        f"💰 Стоимость: {studio.cost} руб.\n"
        f"🎂 Возраст: {studio.age}\n"
        f"🏷 Категория: {studio.category}\n"
        f"ℹ️ {studio.description or 'Нет описания'}"
    )

    await callback.message.answer(text, reply_markup= kb)



# -----------Обработчики ---------------------


@studios_router.message(Command("studios"))
async def show_studios(message: types.Message):
    await start_studios(message)


@studios_router.callback_query(F.data == "studios")
async def studios_callback(callback: CallbackQuery):
    # передаём message (не сам callback), чтобы start_fsm_studios использовал метод answer/edit_text
    await start_studios(callback.message)


async def start_studios(target: types.Message):
    text = "Выберите, какие студии показать:"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆓 Бесплатные", callback_data="studios_free_True")],
            [InlineKeyboardButton(text="💳 Платные", callback_data="studios_free_False")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")],
        ]
    )
    try:
        await target.edit_text(text, reply_markup=kb)
    except Exception:
        await target.answer(text, reply_markup=kb)


@studios_router.callback_query(F.data.startswith("studios_free"))
async def choose_category(callback: CallbackQuery, session: AsyncSession):
    is_free = callback.data.endswith("True")

    # собираем список категорий
    result = await session.execute(select(Studios.category).distinct())
    categories = result.scalars().all()

    buttons = [
        [InlineKeyboardButton(text="📋 Показать все", callback_data=f"std_list_{is_free}_all")]
    ]

    for category in categories:
        display = 'Другое' if category == 'unknown' else (category or 'Не указано')
        # В callback_data передаём оригинальное значение категории (без .lower()), чтобы фильтр был точным
        code = short_code(category)
        CATEGORY_MAP[code] = category  # сохраняем в словарь
        buttons.append([
            InlineKeyboardButton(
                text=display.capitalize(),
                callback_data=f"std_list_{is_free}_{code}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="studios")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        f"Список {'бесплатных' if is_free else 'платных'} категорий студий:",
        reply_markup=kb
    )
    await callback.answer()


# ---------- STEP 3: список студий ----------
@studios_router.callback_query(F.data.startswith("std_list_"))
async def std_list(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    # Ожидаем формат: std_list_{is_free}_<category_or_all>
    _, _, is_free_str, category = callback.data.split("_", 3)
    category = CATEGORY_MAP.get(category)
    is_free = is_free_str == "True"
    category = None if category == "all" else category
    try:
        await callback.message.delete()
    except:
        pass
    await render_studio_list(callback, session, is_free, category, page=1)


@studios_router.callback_query(F.data.startswith("std_p:"))
async def std_p(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    page = int(callback.data.split(":")[1])
    data = callback.data.split("_list_")[1]
    is_free, category = data.split('_')
    category = (None if category == 'all' else CATEGORY_MAP.get(category))
    await render_studio_list(callback, session, is_free == "True", category, page)


@studios_router.callback_query(F.data.startswith("studio_card:"))
async def studio_card(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    # await callback.message.answer(callback.data)
    card, back_mark = callback.data.split('std_list_')
    studio_id, page = card.split(":")[1:3]
    page = page.split("_")[0]

    studio = await orm_get_studio(session, int(studio_id))
    msg_id = callback.message.message_id
    back_mark = f"std_list_{back_mark}"
    data = [back_mark,page,msg_id]

    await render_studio_card(callback,studio, session, data)


@studios_router.callback_query(F.data.startswith("std_dl:"))
async def studio_detail(callback: CallbackQuery, session: AsyncSession):
    studio_id = int(callback.data.split(":")[1])
    query = callback.data.split(":")[-1]
    studio = await orm_get_studio(session, studio_id)
    try:
        await callback.message.delete()
    except:
        pass
    await render_studio_detail(callback,session,studio,query)
    try:
        await callback.message.delete()
    except:
        pass