from gc import callbacks

from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.filters import or_f, Command

from database.models import Studios
from database.orm_query import orm_get_all_studios, orm_get_studio
from sqlalchemy import select, func

user_studios_router = Router()

@user_studios_router.message(or_f(Command('studios'),(F.text.lower()[1:] == "студии")))
async def show_studios(message: types.Message, session: AsyncSession):
    await list_studios(message,session)
    # await  message.answer('____________',callback_data="list_studios")
# ===============================
# СПИСОК СТУДИЙ/
# ===============================
STUDIOS_PER_PAGE = 8


def get_studios_keyboard(studios, page: int, total_pages: int):
    keyboard = [
        [InlineKeyboardButton(
            text=f"{'🆓' if studio.cost == 0 else '💳'} {(studio.name).capitalize()}",
            callback_data=f"studio_detail:{studio.id}"
        )]
        for studio in studios
    ]

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⏮ Назад", callback_data=f"studios_page:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="⏭ Далее", callback_data=f"studios_page:{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def list_studios(message_or_callback, session, page: int = 1):
    PAGE_SIZE = 8
    offset = (page - 1) * PAGE_SIZE
    studios = (await session.execute(
        select(Studios).order_by(Studios.id).offset(offset).limit(PAGE_SIZE)
    )).scalars().all()

    total = (await session.execute(select(func.count(Studios.id)))).scalar_one()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    if not studios:
        if isinstance(message_or_callback, types.CallbackQuery):
            await message_or_callback.answer("Студии не найдены", show_alert=True)
        else:
            await message_or_callback.answer("Студии не найдены")
        return

    text = "Список студий:\n\n"

    keyboard = get_studios_keyboard(studios, page, total_pages)

    if isinstance(message_or_callback, types.CallbackQuery):
        try:
            await message_or_callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception:
            await message_or_callback.message.answer(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    else:  # Message
        await message_or_callback.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@user_studios_router.callback_query(F.data.startswith("studios_page:"))
async def studios_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await list_studios(callback, session, page)