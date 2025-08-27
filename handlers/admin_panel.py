from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from replyes.kbrds import get_keyboard
from aiogram.filters import  Command, or_f
from aiogram import Router, types, F
from filter.filter import ChatTypeFilter, IsAdmin, check_message, get_admins_ids

from data.text import admin_welcome

user_router = Router()
@user_router.message(or_f(Command('check_admin'), lambda msg: msg.text == "Проверить админа"))
async def if_admin(message: types.Message):
    await message.answer(f'Ваш id:\t{message.from_user.id}')
    if  check_message(message):
        await message.answer('✅Вы админ')
    else:
         await message.answer(f'❌У вас нет прав админимстратора')


ADMIN_KB = get_keyboard(
    "Редактировать Новости",
    "Редактировать Афишу",
    "Редактировать Студии",
    "Вернуться",
    placeholder="Выберите действие",
    sizes=(3,1),
)


admin_router = Router()
admin_router.message.filter(ChatTypeFilter(['private']),IsAdmin())


@admin_router.message(or_f(Command('admin_panel'), (lambda msg: msg.text == "🛠Панель администратора")))
async def admin_panel(message: types.Message):
    await message.answer(f'{admin_welcome}', reply_markup=ADMIN_KB)

def admin_panel_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Редактировать Афишу', callback_data="q")],
        [InlineKeyboardButton(text='Редактировать Студии', callback_data="q")],
        [InlineKeyboardButton(text='Редактировать Новости', callback_data="q")],
        [InlineKeyboardButton(text='Редактировать Администраторов', callback_data="q")]
    ])
