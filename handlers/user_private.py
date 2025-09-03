from aiogram import F, types, Router, Bot
from aiogram.filters import CommandStart, Command, or_f
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from filter.filter import ChatTypeFilter, check_message, IsSuperAdmin
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import  orm_add_user
from handlers.menu2 import help_, get_main_menu_kb

from data.text import  welcome, welcome_text


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
    # await help_(callback)
    await callback.message.edit_text(welcome_text, get_main_menu_kb(callback.from_user))

@user_private_router.message(or_f(Command('check_admin'), lambda msg: msg.text == "Проверить админа"))
async def if_admin(message: types.Message):
    await message.answer(f'Ваш id:\t{message.from_user.id}')
    if  check_message(message):
        await message.answer('✅Вы админ')
    else:
         await message.answer(f'❌У вас нет прав админимстратора')
