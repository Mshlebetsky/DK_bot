import logging

from aiogram import F, types, Router, Bot
from aiogram.filters import CommandStart, Command, or_f
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from filter.filter import ChatTypeFilter, check_message, IsSuperAdmin, IsEditor
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import  orm_add_user
from handlers.menu2 import get_main_menu_kb
from logic.helper import get_text

#Подгрузка текста



welcome = get_text("welcome")
welcome_text = get_text("welcome_text")


# ================== ЛОГИРОВАНИЕ ==================

logger = logging.getLogger(__name__)

# ================== РОУТЕР ==================


user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))


@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):

    logger.info(f"Пользователь {message.from_user.id} нажал команду /start")

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
    logger.info(f"Пользователь {callback.from_user.id} согласился с правилами")
    await callback.message.answer(welcome_text, reply_markup=await get_main_menu_kb(callback.from_user, session))


@user_private_router.message(Command('check_id'))
async def if_admin(message: types.Message, bot: Bot, session: AsyncSession):
    try:
        if await IsSuperAdmin()(message, bot=bot):
            role = "super_admin"
        elif await IsEditor()(message, session=session):
            role = "editor"
        else:
            role = "user"

        logger.info(f"User {message.from_user.id} checked role: {role}")
        await message.answer(f"Ваша роль: {role}\n'Ваш id:\t{message.from_user.id}")
    except Exception as e:
        logger.exception(f"Ошибка при проверке роли пользователя {message.from_user.id}: {e}")
        await message.answer("❌ Ошибка при проверке роли.")