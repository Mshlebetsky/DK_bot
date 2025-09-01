from aiogram import F, types, Router, Bot
from aiogram.filters import CommandStart, Command, or_f
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from filter.filter import ChatTypeFilter, check_message
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import orm_get_user, orm_add_user
from handlers.menu2 import get_main_menu_kb, help_, render_main_menu

from replyes.kbrds import get_keyboard
from data.text import contact, menu, welcome

from handlers.Studio_list import render_studio_list
from handlers.Event_list import render_event_list
from handlers.News_list import render_all_news, render_news_card
from handlers.notification import get_subscriptions_kb


user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))


@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):
    # добавляем юзера в базу
    await orm_add_user(
        session,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    policy_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Согласен",
                    callback_data="agree_policy"
                )
            ]
        ]
    )
    await message.answer(f"{welcome}", reply_markup=policy_keyboard, parse_mode="HTML")
@user_private_router.callback_query(F.data == "agree_policy")
async def process_agree(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("Спасибо, вы согласились ✅", show_alert=False)
    # Показываем следующее меню
    await help_(callback)

