from aiogram import types, Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_get_user, orm_add_user
from filter.filter import check_user, ChatTypeFilter
from data.text import contact, help
from handlers.Event_list import render_event_list
from handlers.News_list import render_all_news
from handlers.Serviсes import get_services_kb
from handlers.Studio_list import render_studio_list
from handlers.notification import get_subscriptions_kb


def get_main_menu_kb(user: types.User):
    buttons = [
        [
            InlineKeyboardButton(text="📆Афиша мероприятий", callback_data="list_events"),
            InlineKeyboardButton(text="💃Студии", callback_data="list_studios"),
        ],
        [
            InlineKeyboardButton(text="🗞Новости", callback_data="list_news"),
            InlineKeyboardButton(text="🖍Подписки", callback_data="notifications_"),
        ],
        [
            InlineKeyboardButton(text="💼Услуги", callback_data="services"),
            InlineKeyboardButton(text="📍Контакты", callback_data="contacts"),
        ],
        [InlineKeyboardButton(text="Верификация участника кружков", url="http://uslugi.mosreg.ru")],
        [InlineKeyboardButton(text="💬Помощь", callback_data="help")],
    ]
    if check_user(user):
        buttons.append([InlineKeyboardButton(text="🛠Панель администратора", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


menu2_router = Router()
menu2_router.message.filter(ChatTypeFilter(["private"]))


# ---------- Главное меню ----------
async def render_main_menu(target: types.Message | CallbackQuery, session: AsyncSession):
    text = "🏠 Главное меню"

    if isinstance(target, CallbackQuery):
        user = target.from_user
    elif isinstance(target, types.Message):
        user = target.from_user
    else:
        return

    await orm_add_user(
        session,
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    if isinstance(target, CallbackQuery):
        kb = get_main_menu_kb(target.from_user)
        try:
            await target.message.edit_text(text, reply_markup=kb)
        except Exception:
            await target.message.delete()
            await target.message.answer(text, reply_markup=kb)
        await target.answer()

    elif isinstance(target, types.Message):
        kb = get_main_menu_kb(target.from_user)
        await target.answer(text, reply_markup=kb)


@menu2_router.message(Command("menu"))
async def menu2_(message: types.Message, session: AsyncSession):
    await render_main_menu(message, session)


# ---------- Помощь ----------
@menu2_router.callback_query(F.data == "help")
async def help_(callback_query: CallbackQuery):
    await callback_query.message.edit_text(help, reply_markup=get_main_menu_kb(callback_query.from_user))

@menu2_router.message(Command('help'))
async def help_comand(message: types.Message):
    await message.answer(help, reply_markup=get_main_menu_kb(message.from_user))


# ---------- Главное меню (назад) ----------
@menu2_router.callback_query(F.data == "main_menu")
async def main_menu_(callback: CallbackQuery, bot: Bot, state: FSMContext, session: AsyncSession):
    # проверяем, есть ли сохранённое сообщение с локацией
    data = await state.get_data()
    location_msg_id = data.get("location_msg_id")
    if location_msg_id:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=location_msg_id)
        except Exception:
            pass
        # очищаем из state
        await state.update_data(location_msg_id=None)

    await render_main_menu(callback, session)


# ---------- Контакты ----------
@menu2_router.callback_query(F.data == "contacts")
async def contact_(callback: CallbackQuery, state: FSMContext):
    contact_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Tg", url="https://t.me/mdkjauza"),
                InlineKeyboardButton(text="VK", url="https://vk.com/mdkjauza"),
            ],
            [InlineKeyboardButton(text="🏠 В Главное меню", callback_data='main_menu')]
        ]
    )

    # отправляем локацию и сохраняем её id в FSM
    location_msg = await callback.message.answer_location(55.908752, 37.743256)
    await state.update_data(location_msg_id=location_msg.message_id)

    await callback.message.edit_text(contact, reply_markup=contact_kb)
@menu2_router.message(Command('contact'))
async def contacts_comand(message: types.Message):
    contact_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Tg", url="https://t.me/mdkjauza"),
                InlineKeyboardButton(text="VK", url="https://vk.com/mdkjauza"),
            ],
            [InlineKeyboardButton(text="🏠 В Главное меню", callback_data='main_menu')]
        ]
    )
    await message.answer_location(55.908752, 37.743256)
    await message.answer(contact, reply_markup=contact_kb)

# ---------- Услуги ----------
@menu2_router.callback_query(F.data == "services")
async def services_(callback: CallbackQuery):
    await callback.message.edit_text("Дополнительные услуги", reply_markup=get_services_kb())


#--------------Студии -----------

@menu2_router.message(Command('studios'))
async def show_studios(message: types.Message, session: AsyncSession):
    await render_studio_list(message,session)

# ------------Новости -----------
@menu2_router.message(Command('news'))
async def echo(message: types.Message, session: AsyncSession):
    await render_all_news(message,session)

# ------------Афиша-------------
@menu2_router.message(Command('events'))
async def events_list_command(message: types.Message, session: AsyncSession):
    await render_event_list(message, session, page=1)

#

@menu2_router.message(Command('notification'))
async def notification(message: types.Message, session: AsyncSession):
    await orm_add_user(
        session,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name

    )
    user = await orm_get_user(session, message.from_user.id)
    await message.answer(
        "Выберите подписки:",
        reply_markup=get_subscriptions_kb(user)
    )