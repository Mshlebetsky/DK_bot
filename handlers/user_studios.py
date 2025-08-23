from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import or_f, Command
from database.orm_query import orm_get_all_studios, orm_get_studio
from handlers.user_private import Default_Keyboard
import re

user_studios_router = Router()

# ===============================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ===============================

def is_valid_url(url: str) -> bool:
    # проверка, что ссылка начинается с http:// или https:// и есть хотя бы домен
    pattern = re.compile(r"^https?:\/\/[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}.*$")
    return bool(pattern.match(url))

def get_studios_keyboard(studios, page: int, total_pages: int):
    buttons = []
    for studio in studios:
        buttons.append([
            InlineKeyboardButton(
                text=f"{studio.name} ({studio.age})",
                callback_data=f"studio_detail:{studio.id}"
            )
        ])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"studios_page:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Далее", callback_data=f"studios_page:{page+1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ===============================
# СПИСОК СТУДИЙ
# ===============================

@user_studios_router.message(or_f(Command('studios'),(F.text.lower()[1:] == "студии")))
async def show_studios(message: types.Message, session: AsyncSession):
    items = await orm_get_all_studios(session)

    if not items:
        await message.answer("Пока нет студий")
        return

    page = 1
    page_size = 8
    total_pages = (len(items) + page_size - 1) // page_size

    start = (page - 1) * page_size
    end = start + page_size
    studios_page = items[start:end]

    kb = get_studios_keyboard(studios_page, page, total_pages)
    await message.answer("📚 Список студий:", reply_markup=kb)


# ===============================
# ПАГИНАЦИЯ (далее/назад)
# ===============================

@user_studios_router.callback_query(F.data.startswith("studios_page:"))
async def studios_page_callback(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    items = await orm_get_all_studios(session)

    page_size = 8
    total_pages = (len(items) + page_size - 1) // page_size

    start = (page - 1) * page_size
    end = start + page_size
    studios_page = items[start:end]

    kb = get_studios_keyboard(studios_page, page, total_pages)

    await callback.message.edit_text("📚 Список студий:", reply_markup=kb)
    await callback.answer()


# ===============================
# ПОДРОБНАЯ ИНФОРМАЦИЯ
# ===============================

@user_studios_router.callback_query(F.data.startswith("studio_detail:"))
async def studio_detail_callback(callback: types.CallbackQuery, session: AsyncSession):
    studio_id = int(callback.data.split(":")[1])
    studio = await orm_get_studio(session, studio_id)
    if not studio:
        await callback.message.answer("Студия не найдена.")
        return

    text = (
        f"<b>{studio.name}</b>\n\n"
        f"{studio.description}\n\n"
        f"Категория: {studio.category}\n"
        f"Возраст: {studio.age}\n"
        f"Стоимость: {'Да' if studio.cost else 'Нет'}\n"
    )

    buttons = []

    # # добавляем кнопку только если ссылка корректная
    # if studio.link and is_valid_url(studio.link):
    #     buttons.append([InlineKeyboardButton(text="🔗 Записаться", url=studio.link)])
    # else:
    #     # text += "\n⚠️ Ссылка для записи недоступна"
    #     buttons.append([InlineKeyboardButton(text="🔗 Сайт", url="https://дк-яуза.рф/studii/")])


    # всегда есть кнопка "назад"
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="studios_page:1")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    # if studio.img:
    #     await callback.message.answer_photo(photo=studio.img, caption=text, reply_markup=kb, parse_mode="HTML")
    # else:
    #     await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    #
    # await callback.answer()