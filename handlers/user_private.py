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

keyboard_params =["📆Афиша мероприятий",
            "💃Студии",
            "🗞Новости",
            "📝Меню",
            "💼Услуги",
            "🖍Подписки",
            "📍Контакты",
            "Проверить админа"]

User_Default_KBRD = get_keyboard(
           *keyboard_params,placeholder="Что вас интересует?",sizes=(3, 3, 2)
        )
admin_Keyboard_params = ["📆Афиша мероприятий",
            "💃Студии",
            "🗞Новости",
            "📝Меню",
            "💼Услуги",
            "🖍Подписки",
            "📍Контакты",
            "Проверить админа",
            "🛠Панель администратора"]
Admin_Default_KBRD = get_keyboard(
           *admin_Keyboard_params,placeholder="Что вас интересует?",sizes=(3, 3, 3)#
        )
# def get_main_menu_kb(message: types.Message):
#
#     buttons = [[
#         InlineKeyboardButton(text = '📆Афиша мероприятий', callback_data="list_events"),
#         InlineKeyboardButton(text="💃Студии", callback_data="list_studios")],
#     [
#         InlineKeyboardButton(text="🗞Новости", callback_data="list_events"),
#         InlineKeyboardButton(text="🖍Подписки", callback_data="event_list")],
#     [
#         InlineKeyboardButton(text="💼Услуги", callback_data="services"),
#         InlineKeyboardButton(text="📍Контакты", callback_data="contacts")],
#     [
#         InlineKeyboardButton(text="💬Помощь", callback_data="help"),]]
#     if  check_message(message):
#         buttons.append([InlineKeyboardButton(text="🛠Панель администратора", callback_data="admin_panel")])
#     return InlineKeyboardMarkup(inline_keyboard=buttons)



def Default_Keyboard(message):
    if  check_message(message):
        return  Admin_Default_KBRD
    else:
        return User_Default_KBRD

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
    # # Удаляем сообщение с кнопкой "Согласен"
    # try:
    #     await callback.message.delete()
    # except Exception:
    #     pass

    await callback.answer("Спасибо, вы согласились ✅", show_alert=False)
    # Показываем следующее меню
    await help_(callback)
    # await render_main_menu(callback,session)
    # await callback.message.answer(
    #     f"Теперь можно начать работу:",
        # f"Теперь можно начать работу:\n{menu}",
        # reply_markup=User_Default_KBRD
        # reply_markup=get_main_menu_kb(callback.from_user)
    # )

@user_private_router.message(or_f(Command('menu'),(F.data == "start_work"),(F.text.lower()[1:] == "меню"),(F.text.lower() == "вернуться")))
async def show_menu(message: types.Message):
    await message.answer(f'{menu}',reply_markup= Default_Keyboard(message))
    # await message.answer(f'{menu}', reply_markup=get_main_menu_kb(message))

@user_private_router.message(or_f(Command('contact'),(F.text.lower()[1:] == ("контакты"))))
async def echo(message: types.Message):
    await message.answer(contact)
    await message.answer_location(55.908752,37.743256, reply_markup= Default_Keyboard(message))



@user_private_router.message(or_f(Command('studios'),(F.text.lower()[1:] == "студии")))
async def show_studios(message: types.Message, session: AsyncSession):
    await render_studio_list(message,session)


@user_private_router.message(or_f(Command('news'),(F.text.lower()[1:] == "новости")))
async def echo(message: types.Message, session: AsyncSession):
    await render_all_news(message,session)

@user_private_router.message(or_f(Command('events'),(F.text == "📆Афиша мероприятий")))
async def events_list_command(message: types.Message, session: AsyncSession):
    await render_event_list(message, session, page=1)

@user_private_router.message(or_f(Command('notification'),(F.text == "🖍Подписки")))
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