from aiogram import Router, F, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from database.models import News
from database.orm_query import orm_get_news

news_router = Router()

NEWS_PER_PAGE = 8


# ---------- Клавиатуры ----------
def get_news_card_keyboard(news_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[

                [InlineKeyboardButton(text="📋 Все новости", callback_data="list_all_news"),
                InlineKeyboardButton(text="ℹ Подробнее", callback_data=f"news_detail:{news_id}")],
                [InlineKeyboardButton(text="⏮ Назад", callback_data=f"news_next:{news_id}"),
                InlineKeyboardButton(text="⏭ Далее", callback_data=f"news_prev:{news_id}")],
            ]

    )


def get_all_news_keyboard(news, page: int, total_pages: int):
    keyboard = [
        [InlineKeyboardButton(
            text=new.name[:40],  # ограничим длину названия
            callback_data=f"news_card:{new.id}"
        )]
        for new in news
    ]

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⏮ Назад", callback_data=f"all_news_page:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="⏭ Далее", callback_data=f"all_news_page:{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ---------- Рендеры ----------
async def render_news_card(message_or_callback, session: AsyncSession, news_id: int):
    news = await orm_get_news(session, news_id)
    if not news:
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer("Новость не найдена", show_alert=True)
        else:
            await message_or_callback.answer("Новость не найдена")
        return

    description = news.description or "Нет описания"
    short_desc = description[:350] + ("… \nнажмите на \"подробднее\", чтобы прочитать полностью" if len(description) > 350 else "")

    # соседи для списка
    neighbors = (
        await session.execute(
            select(News)
            .where(News.is_shown == True)
            .order_by(desc(News.id))
        )
    ).scalars().all()

    idx = next((i for i, n in enumerate(neighbors) if n.id == news.id), None)
    neighbor_titles = []
    if idx is not None:
        # предыдущая новость
        if idx > 0:
            prev_news = neighbors[idx - 1]
            short_name = prev_news.name[:100] + ("…" if len(prev_news.name) > 100 else "")
            neighbor_titles.append(
                f"⬅ <i>Предыдущая:</i> \n🗞 {short_name}"
            )

        # следующие новости
        next_two = neighbors[idx + 1: idx + 3]
        if next_two:
            titles = "\n".join(
                [f"🗞 {n.name[:100] + ("…" if len(n.name) > 100 else "")}" for n in next_two]
            )
            neighbor_titles.append(f"➡ <i>Следующие:</i>\n{titles}")

    text = f"<b>{news.name}</b>\n\n{short_desc}\n\n" + "\n".join(neighbor_titles)
    kb = get_news_card_keyboard(news.id)

    target = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

    try:
        if news.img:
            # если есть картинка — всегда удаляем предыдущее сообщение
            await target.delete()
            await target.answer_photo(news.img, caption=text[:1024], reply_markup=kb, parse_mode="HTML")
        else:
            # если только текст
            if target.text:
                await target.edit_text(text[:4095], reply_markup=kb, parse_mode="HTML")
            else:
                await target.delete()
                await target.answer(text[:4095], reply_markup=kb, parse_mode="HTML")
    except Exception:
        await target.answer(text[:4095], reply_markup=kb, parse_mode="HTML")

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.answer()



async def render_news_detail(message_or_callback, session: AsyncSession, news: News):
    """Полная карточка новости"""
    text = f"<b>{news.name}</b>\n\n{news.description or 'Нет описания'}"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"news_card:{news.id}")],
            [InlineKeyboardButton(text="🔗 Перейти на сайт", url="https://дк-яуза.рф/news/")]
        ]
    )

    target = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

    try:
        if news.img:
            await target.delete()
            await target.answer_photo(news.img, caption=text[:1024], reply_markup=kb, parse_mode="HTML")
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



async def render_all_news(message_or_callback, session: AsyncSession, page: int = 1):
    """Список всех новостей"""
    offset = (page - 1) * NEWS_PER_PAGE
    news = (
        await session.execute(
            select(News).where(News.is_shown == True).order_by(desc(News.id)).offset(offset).limit(NEWS_PER_PAGE)
        )
    ).scalars().all()

    total = (await session.execute(select(func.count(News.id)))).scalar_one()
    total_pages = (total + NEWS_PER_PAGE - 1) // NEWS_PER_PAGE

    text = "📋 <b>Список новостей:</b>\n\n"
    keyboard = get_all_news_keyboard(news, page, total_pages)

    target = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

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


# ---------- Хендлеры ----------
@news_router.callback_query(F.data == "list_news")
async def list_news_handler(callback: CallbackQuery, session: AsyncSession):
    # сразу показываем последнюю добавленную новость
    last_news = (
        await session.execute(
            select(News).where(News.is_shown == True).order_by(desc(News.id)).limit(1)
        )
    ).scalars().first()
    if last_news:
        await render_news_card(callback, session, last_news.id)
    else:
        await callback.answer("Новостей нет", show_alert=True)


@news_router.callback_query(F.data.startswith("news_card:"))
async def news_card_handler(callback: CallbackQuery, session: AsyncSession):
    news_id = int(callback.data.split(":")[1])
    await render_news_card(callback, session, news_id)


@news_router.callback_query(F.data.startswith("news_detail:"))
async def news_detail_handler(callback: CallbackQuery, session: AsyncSession):
    news_id = int(callback.data.split(":")[1])
    news = await orm_get_news(session, news_id)
    if news:
        await render_news_detail(callback, session, news)



@news_router.callback_query(F.data == "list_all_news")
async def list_all_news_handler(callback: CallbackQuery, session: AsyncSession):
    await render_all_news(callback, session, page=1)


@news_router.callback_query(F.data.startswith("all_news_page:"))
async def all_news_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await render_all_news(callback, session, page)


# переходы назад/вперед
@news_router.callback_query(F.data.startswith("news_prev:"))
async def news_prev_handler(callback: CallbackQuery, session: AsyncSession):
    current_id = int(callback.data.split(":")[1])
    prev_news = (
        await session.execute(
            select(News).where(News.is_shown == True, News.id < current_id).order_by(desc(News.id)).limit(1)
        )
    ).scalars().first()
    if prev_news:
        await render_news_card(callback, session, prev_news.id)
    else:
        await callback.answer("Это самая старая новость")


@news_router.callback_query(F.data.startswith("news_next:"))
async def news_next_handler(callback: CallbackQuery, session: AsyncSession):
    current_id = int(callback.data.split(":")[1])
    next_news = (
        await session.execute(
            select(News).where(News.is_shown == True, News.id > current_id).order_by(News.id).limit(1)
        )
    ).scalars().first()
    if next_news:
        await render_news_card(callback, session, next_news.id)
    else:
        await callback.answer("Это последняя новость")
