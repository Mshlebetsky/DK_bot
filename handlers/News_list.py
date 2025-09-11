import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from database.models import News
from database.orm_query import orm_get_news
from logic.helper import Big_litter_start

# --- Router ---
news_router = Router()

# --- Config ---
NEWS_PER_PAGE = 8

# --- Logger ---
logger = logging.getLogger('bot.handlers.news_list')


# ---------- Клавиатуры ----------
def get_news_card_keyboard(news_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для карточки новости"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Все новости", callback_data="list_all_news"),
                InlineKeyboardButton(text="ℹ Подробнее", callback_data=f"news_detail:{news_id}")
            ],
            [
                InlineKeyboardButton(text="⏮ Назад", callback_data=f"news_next:{news_id}"),
                InlineKeyboardButton(text="⏭ Далее", callback_data=f"news_prev:{news_id}")
            ],
            [InlineKeyboardButton(text="🏠 В Главное меню", callback_data="main_menu")]
        ]
    )


def get_all_news_keyboard(news: list[News], page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для списка новостей"""
    keyboard = [
        [InlineKeyboardButton(
            text=Big_litter_start(n.name[:40]),
            callback_data=f"news_card:{n.id}"
        )]
        for n in news
    ]

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⏮ Назад", callback_data=f"all_news_page:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="⏭ Далее", callback_data=f"all_news_page:{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)
        keyboard.append([InlineKeyboardButton(text="🏠 В Главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ---------- Рендеры ----------
async def render_news_card(target: Message | CallbackQuery, session: AsyncSession, news_id: int):
    """Отображение карточки новости"""
    try:
        news = await orm_get_news(session, news_id)
        if not news:
            logger.warning("Новость с id=%s не найдена", news_id)
            text = "❌ Новость не найдена"
            if isinstance(target, CallbackQuery):
                await target.answer(text, show_alert=True)
            else:
                await target.answer(text)
            return

        description = news.description or "Нет описания"
        short_desc = description[:350] + (
            "<i>… \n\nнажмите на <b>\"Подробнее\"</b> чтобы посмотреть больше</i>"
            if len(description) > 350 else ""
        )

        # Соседи для навигации
        neighbors = (
            await session.execute(
                select(News).where(News.is_shown.is_(True)).order_by(desc(News.id))
            )
        ).scalars().all()

        idx = next((i for i, n in enumerate(neighbors) if n.id == news.id), None)
        neighbor_titles = []
        if idx is not None:
            if idx > 0:
                prev_news = neighbors[idx - 1]
                short_name = prev_news.name[:100] + ("…" if len(prev_news.name) > 100 else "")
                neighbor_titles.append(f"⬅ <i>Предыдущая:</i> \n🗞 {Big_litter_start(short_name)}")

            next_two = neighbors[idx + 1: idx + 3]
            if next_two:
                titles = "\n".join(
                    f"🗞 {Big_litter_start(n.name[:100]) + ('…' if len(n.name) > 100 else '')}"
                    for n in next_two
                )
                neighbor_titles.append(f"➡ <i>Следующие:</i>\n{titles}")

        text = f"<b>{Big_litter_start(news.name)}</b>\n\n{short_desc}\n\n" + "\n".join(neighbor_titles)
        kb = get_news_card_keyboard(news.id)

        msg_target = target.message if isinstance(target, CallbackQuery) else target
        try:
            if news.img:
                await msg_target.delete()
                await msg_target.answer_photo(news.img, caption=text[:1024], reply_markup=kb, parse_mode="HTML")
            else:
                if getattr(msg_target, "text", None):
                    await msg_target.edit_text(text[:4095], reply_markup=kb, parse_mode="HTML")
                else:
                    await msg_target.delete()
                    await msg_target.answer(text[:4095], reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.exception("Ошибка при отправке карточки новости: %s", e)
            await msg_target.answer(text[:4095], reply_markup=kb, parse_mode="HTML")

        if isinstance(target, CallbackQuery):
            await target.answer()

    except Exception as e:
        logger.exception("Ошибка в render_news_card: %s", e)


async def render_news_detail(target: Message | CallbackQuery, news: News):
    """Полная карточка новости"""
    try:
        text = f"<b>{news.name}</b>\n\n{news.description or 'Нет описания'}"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"news_card:{news.id}")],
                [InlineKeyboardButton(text="🔗 Перейти на сайт", url="https://дк-яуза.рф/news/")]
            ]
        )

        msg_target = target.message if isinstance(target, CallbackQuery) else target
        try:
            if news.img:
                await msg_target.delete()
                await msg_target.answer_photo(news.img, caption=text[:1024], reply_markup=kb, parse_mode="HTML")
            else:
                if getattr(msg_target, "text", None):
                    await msg_target.edit_text(text[:4095], reply_markup=kb, parse_mode="HTML")
                else:
                    await msg_target.delete()
                    await msg_target.answer(text[:4095], reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.exception("Ошибка при отправке полной карточки новости: %s", e)
            await msg_target.answer(text[:4095], reply_markup=kb, parse_mode="HTML")

        if isinstance(target, CallbackQuery):
            await target.answer()

    except Exception as e:
        logger.exception("Ошибка в render_news_detail: %s", e)


async def render_all_news(target: Message | CallbackQuery, session: AsyncSession, page: int = 1):
    """Список всех новостей"""
    try:
        offset = (page - 1) * NEWS_PER_PAGE
        news = (
            await session.execute(
                select(News).where(News.is_shown.is_(True)).order_by(desc(News.id)).offset(offset).limit(NEWS_PER_PAGE)
            )
        ).scalars().all()

        total = (await session.execute(select(func.count(News.id)))).scalar_one()
        total_pages = (total + NEWS_PER_PAGE - 1) // NEWS_PER_PAGE

        text = "📋 <b>Список новостей:</b>\n\n"
        keyboard = get_all_news_keyboard(news, page, total_pages)

        msg_target = target.message if isinstance(target, CallbackQuery) else target
        try:
            if getattr(msg_target, "text", None):
                await msg_target.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await msg_target.delete()
                await msg_target.answer(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            logger.exception("Ошибка при отправке списка новостей: %s", e)
            await msg_target.answer(text, reply_markup=keyboard, parse_mode="HTML")

        if isinstance(target, CallbackQuery):
            await target.answer()

    except Exception as e:
        logger.exception("Ошибка в render_all_news: %s", e)


# ---------- Хендлеры ----------
@news_router.callback_query(F.data == "list_news")
async def list_news_handler(callback: CallbackQuery, session: AsyncSession):
    """Показать последнюю новость"""
    try:
        last_news = (
            await session.execute(
                select(News).where(News.is_shown.is_(True)).order_by(desc(News.id)).limit(1)
            )
        ).scalars().first()

        if last_news:
            await render_news_card(callback, session, last_news.id)
        else:
            await callback.answer("❌ Новостей нет", show_alert=True)

    except Exception as e:
        logger.exception("Ошибка в list_news_handler: %s", e)
        await callback.answer("⚠ Ошибка при загрузке новостей", show_alert=True)


@news_router.callback_query(F.data.startswith("news_card:"))
async def news_card_handler(callback: CallbackQuery, session: AsyncSession):
    news_id = int(callback.data.split(":")[1])
    await render_news_card(callback, session, news_id)


@news_router.callback_query(F.data.startswith("news_detail:"))
async def news_detail_handler(callback: CallbackQuery, session: AsyncSession):
    news_id = int(callback.data.split(":")[1])
    news = await orm_get_news(session, news_id)
    if news:
        await render_news_detail(callback, news)
    else:
        await callback.answer("Новость не найдена", show_alert=True)


@news_router.callback_query(F.data == "list_all_news")
async def list_all_news_handler(callback: CallbackQuery, session: AsyncSession):
    await render_all_news(callback, session, page=1)


@news_router.callback_query(F.data.startswith("all_news_page:"))
async def all_news_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await render_all_news(callback, session, page)


@news_router.callback_query(F.data.startswith("news_prev:"))
async def news_prev_handler(callback: CallbackQuery, session: AsyncSession):
    """Перейти к предыдущей новости"""
    current_id = int(callback.data.split(":")[1])
    prev_news = (
        await session.execute(
            select(News).where(News.is_shown.is_(True), News.id < current_id).order_by(desc(News.id)).limit(1)
        )
    ).scalars().first()

    if prev_news:
        await render_news_card(callback, session, prev_news.id)
    else:
        await callback.answer("Это самая старая новость")


@news_router.callback_query(F.data.startswith("news_next:"))
async def news_next_handler(callback: CallbackQuery, session: AsyncSession):
    """Перейти к следующей новости"""
    current_id = int(callback.data.split(":")[1])
    next_news = (
        await session.execute(
            select(News).where(News.is_shown.is_(True), News.id > current_id).order_by(News.id).limit(1)
        )
    ).scalars().first()

    if next_news:
        await render_news_card(callback, session, next_news.id)
    else:
        await callback.answer("Это последняя новость")