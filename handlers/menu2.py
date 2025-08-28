from gc import callbacks

from aiogram import types, Dispatcher, Router, F
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command

from filter.filter import check_message, ChatTypeFilter


def get_main_menu_kb(message: types.Message):

    buttons = [[
        InlineKeyboardButton(text = '📆Афиша мероприятий', callback_data="list_events"),
        InlineKeyboardButton(text="💃Студии", callback_data="list_studios")],
    [
        InlineKeyboardButton(text="🗞Новости", callback_data="list_events"),
        InlineKeyboardButton(text="🖍Подписки", callback_data="event_list")],
    [
        InlineKeyboardButton(text="💼Услуги", callback_data="services"),
        InlineKeyboardButton(text="📍Контакты", callback_data="contacts")],
    [
        InlineKeyboardButton(text="💬Помощь", callback_data="help"),]]
    if  check_message(message):
        buttons.append([InlineKeyboardButton(text="🛠Панель администратора", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

menu2_router = Router()
menu2_router.message.filter(ChatTypeFilter(["private"]))
def render_main_menu():
    text = 'Добро пожаловать в тестовое главное меню'
    await
@menu2_router.message(Command('menu2'))
async def menu2_(message: types.Message):
    await message.answer('Тестовая страница второго меню', reply_markup=get_main_menu_kb(message))

from data.text import menu
@menu2_router.callback_query(F.data == 'help')
async def help_(callback_query: CallbackQuery):
    await callback_query.message.edit_text(menu, reply_markup=get_main_menu_kb(callback_query.message))

@menu2_router.callback_query