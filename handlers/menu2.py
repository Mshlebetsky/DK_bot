import logging
from aiogram import types, Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_get_user, orm_add_user, orm_last_seen_time_user
from filter.filter import ChatTypeFilter, get_user_role
from data.text import contact, help
from handlers.Event_list import render_event_list
from handlers.News_list import render_all_news
from handlers.Serviсes import get_services_keyboard
# from handlers.Studio_list import render_studio_list
from handlers.notification import get_subscriptions_kb

# ================== ЛОГИРОВАНИЕ ==================

logger = logging.getLogger(__name__)

# ================== РОУТЕР ==================


menu2_router = Router()
menu2_router.message.filter(ChatTypeFilter(["private"]))


# ---------- Главное меню ----------
async def get_main_menu_kb(user: types.User, session: AsyncSession) -> InlineKeyboardMarkup:
    role = await get_user_role(user.id, session)
    buttons = [
        [
            InlineKeyboardButton(text="📆 Афиша мероприятий", callback_data="events"),
            InlineKeyboardButton(text="💃 Студии", callback_data="studios"),
        ],
        [
            InlineKeyboardButton(text="🗞 Новости", callback_data="list_news"),
            InlineKeyboardButton(text="🖍 Подписки", callback_data="notifications_"),
        ],
        [
            InlineKeyboardButton(text="💼 Услуги", callback_data="services"),
            InlineKeyboardButton(text="📍 Контакты", callback_data="contacts"),
        ],
        [InlineKeyboardButton(text="Верификация участника кружков", url="http://uslugi.mosreg.ru")],
        [InlineKeyboardButton(text="💬 Помощь", callback_data="help")],
    ]
    if role != "user":
        buttons.append([InlineKeyboardButton(text="🛠 Панель администратора", callback_data="admin_panel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def render_main_menu(target: types.Message | CallbackQuery, session: AsyncSession):
    """Рендер главного меню."""
    text = "🏠 Главное меню"

    if isinstance(target, (types.Message, CallbackQuery)):
        user = target.from_user
    else:
        logger.warning("Попытка рендера главного меню для неизвестного объекта: %s", type(target))
        return
    try:
        # Добавляем пользователя в БД
        await orm_add_user(
            session,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
    except Exception as e:
        logger.warning(f"Не удалось добавить пользователя при рендере главного меню {e}")
        pass
    try:
        await orm_last_seen_time_user(session, user.id)
    except Exception as e:
        logger.warning(f"Не удалось обновить время последнего визита пользователя {e}")
        pass
    logger.info("Пользователь %s (%s) вошел в главное меню", user.id, user.username)

    kb = await get_main_menu_kb(user, session)

    if isinstance(target, CallbackQuery):
        try:
            try:
                await target.message.edit_text(text, reply_markup=kb)
            except:
                pass
        except Exception as e:
            # logger.warning("Не удалось отредактировать главное меню, отправляем новое сообщение: %s", e)
            await target.message.delete()
            await target.message.answer(text, reply_markup=kb)
        await target.answer()

    elif isinstance(target, types.Message):
        await target.answer(text, reply_markup=kb)


@menu2_router.message(Command("menu"))
async def menu2_(message: types.Message, session: AsyncSession):
    await render_main_menu(message, session)


# ---------- Помощь ----------
@menu2_router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery, session: AsyncSession):
    logger.info("Пользователь %s запросил помощь", callback.from_user.id)
    try:
        await callback.message.edit_text(help, reply_markup=await get_main_menu_kb(callback.from_user, session))
    except Exception as e:
        logger.warning("Не удалось показать help (callback): %s", e)


@menu2_router.message(Command("help"))
async def help_command(message: types.Message, session: AsyncSession):
    logger.info("Пользователь %s вызвал команду /help", message.from_user.id)
    try:
        await message.answer(help, reply_markup=await get_main_menu_kb(message.from_user, session))
    except Exception as e:
        logger.warning("Не удалось показать help (command): %s", e)


# ---------- Главное меню (назад) ----------
@menu2_router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, bot: Bot, state: FSMContext, session: AsyncSession):
    logger.info("Пользователь %s вернулся в главное меню", callback.from_user.id)

    # Проверяем, есть ли сохранённое сообщение с локацией
    data = await state.get_data()
    location_msg_id = data.get("location_msg_id")
    if location_msg_id:
        try:
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=location_msg_id)
            logger.info("Удалено сообщение с локацией %s для пользователя %s", location_msg_id, callback.from_user.id)
        except Exception as e:
            logger.warning("Не удалось удалить сообщение с локацией %s: %s", location_msg_id, e)

        await state.update_data(location_msg_id=None)

    await render_main_menu(callback, session)


# ---------- Контакты ----------
@menu2_router.callback_query(F.data == "contacts")
async def contacts_callback(callback: CallbackQuery, state: FSMContext):
    logger.info("Пользователь %s запросил контакты", callback.from_user.id)

    contact_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Tg", url="https://t.me/mdkjauza"),
                InlineKeyboardButton(text="VK", url="https://vk.com/mdkjauza"),
            ],
            [InlineKeyboardButton(text="🏠 В Главное меню", callback_data="main_menu")],
        ]
    )

    # Отправляем локацию и сохраняем её id в FSM
    location_msg = await callback.message.answer_location(55.908752, 37.743256)
    await state.update_data(location_msg_id=location_msg.message_id)
    logger.info("Сохранено сообщение с локацией %s для пользователя %s", location_msg.message_id, callback.from_user.id)

    await callback.message.edit_text(contact, reply_markup=contact_kb)


@menu2_router.message(Command("contact"))
async def contacts_command(message: types.Message, state: FSMContext):
    logger.info("Пользователь %s вызвал команду /contact", message.from_user.id)

    contact_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Tg", url="https://t.me/mdkjauza"),
                InlineKeyboardButton(text="VK", url="https://vk.com/mdkjauza"),
            ],
            [InlineKeyboardButton(text="🏠 В Главное меню", callback_data="main_menu")],
        ]
    )
    await message.answer(contact, reply_markup=contact_kb)

    location_msg = await message.answer_location(55.908752, 37.743256)
    await state.update_data(location_msg_id=location_msg.message_id)
    logger.info("Сохранено сообщение с локацией %s для пользователя %s", location_msg.message_id, message.from_user.id)


# ---------- Услуги ----------
@menu2_router.callback_query(F.data == "services")
async def services_callback(callback: CallbackQuery):
    logger.info("Пользователь %s открыл раздел услуги", callback.from_user.id)
    await callback.message.edit_text("Дополнительные услуги", reply_markup=get_services_keyboard())


# ---------- Новости ----------
@menu2_router.message(Command("news"))
async def news_command(message: types.Message, session: AsyncSession):
    logger.info("Пользователь %s вызвал команду /news", message.from_user.id)
    await render_all_news(message, session)


# ---------- Подписки ----------
@menu2_router.message(Command("notification"))
async def notification_command(message: types.Message, session: AsyncSession):
    logger.info("Пользователь %s вызвал команду /notification", message.from_user.id)

    await orm_add_user(
        session,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    user = await orm_get_user(session, message.from_user.id)
    await message.answer("Выберите подписки:", reply_markup=get_subscriptions_kb(user))




# # ---------- Афиша ----------
# @menu2_router.message(Command("events"))
# async def events_command(message: types.Message, session: AsyncSession):
#     logger.info("Пользователь %s вызвал команду /events", message.from_user.id)
#     await render_event_list(message, session, page=1)