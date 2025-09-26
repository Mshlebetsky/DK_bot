import logging
import json

from aiogram import Router, types, F, Bot
from aiogram.filters import Command, or_f
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from filter.filter import ChatTypeFilter, IsAdmin, IsEditor, IsSuperAdmin, get_user_role
from database.models import Admin, Users
from handlers.notification import send_event_reminders, notify_all_users
from logic.cmd_list import private
from logic.helper import load_texts, save_texts, get_text


# ================== ЛОГИРОВАНИЕ ==================

logger = logging.getLogger(__name__)

# ================== РОУТЕРЫ ==================


admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

admin_manage_router = Router()
admin_manage_router.message.filter(or_f(IsSuperAdmin(), IsEditor()))


# --- Role check ---
@admin_manage_router.message(Command("check"))
async def check_(message: types.Message, bot: Bot, session: AsyncSession):
    try:
        if await IsSuperAdmin()(message, bot=bot):
            role = "super_admin"
        elif await IsEditor()(message, session=session):
            role = "editor"
        else:
            role = "user"

        logger.info(f"User {message.from_user.id} checked role: {role}")
        await message.answer(f"Ваша роль: {role}")
    except Exception as e:
        logger.exception(f"Ошибка при проверке роли пользователя {message.from_user.id}: {e}")
        await message.answer("❌ Ошибка при проверке роли.")


# --- Admin panel menu ---
async def admin_panel_menu(user: types.User, bot: Bot, session: AsyncSession) -> InlineKeyboardMarkup:
    role = await get_user_role(user.id, session)

    buttons = [
        [InlineKeyboardButton(text="Редактировать Афишу", callback_data="edit_events_panel")],
        [InlineKeyboardButton(text="Редактировать Студии", callback_data="edit_studios_panel")],
        [InlineKeyboardButton(text="Редактировать Новости", callback_data="edit_news_panel")],
    ]

    if role == "super_admin":
        buttons.append([InlineKeyboardButton(text="Редактировать Администраторов", callback_data="manage_editors")])
        buttons.append([InlineKeyboardButton(text="Изменить текст вкладок", callback_data="change_fields")])
        buttons.append([InlineKeyboardButton(text="Отправить всем!📢", callback_data="notify_all_start")])

    buttons.append([InlineKeyboardButton(text="🏠 В Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@admin_manage_router.message(Command("admin"))
async def admin_panel(message: types.Message, bot: Bot, session: AsyncSession):
    logger.info(f"User {message.from_user.id} открыл админ-панель")
    await message.answer(get_text("admin_welcome"), reply_markup=await admin_panel_menu(message.from_user, bot, session))


@admin_manage_router.callback_query(F.data == "admin_panel")
async def admin_menu_callback(callback: CallbackQuery, bot: Bot, session: AsyncSession):
    logger.info(f"User {callback.from_user.id} вернулся в админ-панель")
    await callback.message.edit_text(get_text("admin_welcome"), reply_markup=await admin_panel_menu(callback.from_user, bot, session))


# --- Manage editors ---
@admin_router.callback_query(F.data == "manage_editors")
async def manage_editors(callback: CallbackQuery, session: AsyncSession):
    editors = (await session.execute(select(Admin))).scalars().all()
    logger.info(f"Найдено {len(editors)} редакторов")

    text = "🛠 Управление редакторами:\n\n"
    for ed in editors:
        user = await session.get(Users, ed.user_id)
        if user:
            name_parts = [n for n in [user.first_name, user.last_name] if n]
            full_name = " ".join(name_parts) if name_parts else "—"
            username = f"@{user.username}" if user.username else ""
            display = f"{full_name} {username}".strip()
        else:
            display = "❌ Не найден в Users"
        text += f"• {ed.user_id} ({ed.role}) — {display}\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить редактора", callback_data="add_editor")],
            [InlineKeyboardButton(text="➖ Удалить редактора", callback_data="remove_editor")],
            [InlineKeyboardButton(text="🏠 Назад", callback_data="admin_panel")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb)


class EditorFSM(StatesGroup):
    add_id = State()
    remove_id = State()


@admin_router.callback_query(F.data == "add_editor")
async def add_editor(callback: CallbackQuery, state: FSMContext):
    logger.debug(f"Пользователь {callback.from_user.id} начал добавление редактора")
    await callback.message.answer("Отправьте ID пользователя, которого хотите назначить редактором.")
    await state.set_state(EditorFSM.add_id)


@admin_router.callback_query(F.data == "remove_editor")
async def remove_editor(callback: CallbackQuery, state: FSMContext):
    logger.debug(f"Пользователь {callback.from_user.id} начал удаление редактора")
    await callback.message.answer("Отправьте ID пользователя, которого хотите удалить из редакторов.")
    await state.set_state(EditorFSM.remove_id)


@admin_router.message(EditorFSM.add_id)
async def editor_add_handler(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        user_id = int(message.text)
        session.add(Admin(user_id=user_id, role="editor"))
        await session.commit()
        logger.debug(f"Добавлен новый редактор {user_id}")
        await message.answer(f"✅ Пользователь {user_id} назначен редактором")
    except Exception as e:
        logger.exception(f"Ошибка при добавлении редактора {message.text}: {e}")
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()


@admin_router.message(EditorFSM.remove_id)
async def editor_remove_handler(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        user_id = int(message.text)
        await session.execute(delete(Admin).where(Admin.user_id == user_id))
        await session.commit()
        logger.debug(f"Редактор {user_id} удалён")
        await message.answer(f"✅ Пользователь {user_id} удален из редакторов")
    except Exception as e:
        logger.exception(f"Ошибка при удалении редактора {message.text}: {e}")
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()


# --- Bot menu setup ---
@admin_router.message(Command("set_menu"))
async def set_menu(message: types.Message, bot: Bot):
    logger.info(f"User {message.from_user.id} установил меню команд")
    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
    await message.answer("✅ Команды меню успешно установлены. Если они не появились, очистите историю с ботом.")


# --- Event reminders ---
@admin_router.message(Command("send_reminders"))
async def send_reminders(message: types.Message, session: AsyncSession, bot: Bot):
    logger.info(f"User {message.from_user.id} отправил тестовые напоминания")
    await send_event_reminders(bot, session)
    await message.answer("Тестовые напоминания отправлены!")


# --- Notify all users ---
class NotifyAll(StatesGroup):
    text = State()
    choose_img = State()
    img = State()
    confirm = State()


@admin_router.message(Command("notify_all_users"))
async def notify_all_cmd(message: types.Message):
    logger.info(f"User {message.from_user.id} запустил рассылку")
    await message.answer(
        "Отправить уведомление всем пользователям?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data="notify_all_start")],
                [InlineKeyboardButton(text="Нет", callback_data="main_menu")],
            ]
        ),
    )


@admin_router.callback_query(F.data == "notify_all_start")
async def notify_start(callback: CallbackQuery, state: FSMContext):
    logger.debug(f"User {callback.from_user.id} начал создание рассылки")
    await state.set_state(NotifyAll.text)
    await callback.message.answer("Введите текст уведомления:")
    await callback.answer()


@admin_router.message(NotifyAll.text)
async def notify_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(NotifyAll.choose_img)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить фото", callback_data="notify_add_img")],
            [InlineKeyboardButton(text="❌ Без фото", callback_data="notify_no_img")],
        ]
    )

    logger.debug(f"Пользователь {message.from_user.id} задал текст рассылки")
    await message.answer("Хотите прикрепить фото?", reply_markup=kb)


@admin_router.callback_query(F.data == "notify_add_img")
async def notify_add_img(callback: CallbackQuery, state: FSMContext):
    logger.debug(f"Пользователь {callback.from_user.id} прикрепляет фото к рассылке")
    await state.set_state(NotifyAll.img)
    await callback.message.answer("Отправьте ссылку (URL) на изображение:")
    await callback.answer()


@admin_router.callback_query(F.data == "notify_no_img")
async def notify_no_img(callback: CallbackQuery, state: FSMContext):
    logger.debug(f"Пользователь {callback.from_user.id} выбрал рассылку без фото")
    await state.update_data(img=None)
    await show_preview(callback.message, state)
    await callback.answer()


@admin_router.message(NotifyAll.img)
async def notify_img(message: types.Message, state: FSMContext):
    await state.update_data(img=message.text)
    logger.debug(f"Пользователь {message.from_user.id} добавил фото для рассылки")
    await show_preview(message, state)


async def show_preview(message_or_callback, state: FSMContext):
    data = await state.get_data()
    text = data["text"]
    img = data.get("img")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить", callback_data="notify_confirm")],
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="notify_all_start")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")],
        ]
    )
    try:
        if img:
            await message_or_callback.answer_photo(img, caption=f"{text}\n\nОтправить?", reply_markup=kb)
            logger.debug("Предпросмотр рассылки с фото отправлен")
        else:
            await message_or_callback.answer(f"{text}\n\nОтправить?", reply_markup=kb)
            logger.debug("Предпросмотр рассылки без фото отправлен")
    except Exception as e:
        logger.warning(f"Не удалось отправить предпросмотр: {e}")
        await message_or_callback.answer(
            f"❌ Ошибка: {e}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Попробовать ещё раз", callback_data="notify_all_start")],
                    [InlineKeyboardButton(text="🏠 В Главное меню", callback_data="main_menu")],
                ]
            ),
        )
    await state.set_state(NotifyAll.confirm)


@admin_router.callback_query(F.data == "notify_confirm")
async def notify_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession):
    data = await state.get_data()
    await state.clear()

    text = data["text"]
    img = data.get("img")

    logger.info(f"Пользователь {callback.from_user.id} подтвердил рассылку")
    await notify_all_users(bot, session, text, img)
    await callback.message.answer("✅ Уведомление отправлено!")
    await callback.answer()


#Редактирование текста
# Состояния FSM
class EditText(StatesGroup):
    choosing_key = State()
    editing_value = State()


@admin_router.callback_query(F.data == "change_fields")
async def change_fields(callback: CallbackQuery, state: FSMContext):
    texts = load_texts()
    kb = InlineKeyboardBuilder()
    for key in texts.keys():
        kb.button(text=key, callback_data=f"edit_text:{key}")
    kb.button(text="🛠 В Панель администратора", callback_data="admin_panel")
    kb.adjust(1)
    await callback.message.answer("Выберите раздел для редактирования:", reply_markup=kb.as_markup())
    await state.set_state(EditText.choosing_key)


# Выбор ключа
@admin_router.callback_query(F.data.startswith("edit_text:"))
async def choose_text_key(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":")[1]
    texts = load_texts()
    current = texts.get(key, "")
    await state.update_data(key=key)
    await callback.message.answer(f"Текущий текст для <b>{key}</b>:\n\n{current}\n\nОтправьте новый текст:")
    await state.set_state(EditText.editing_value)

# Приём нового значения
@admin_router.message(EditText.editing_value)
async def receive_new_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    key = data["key"]
    texts = load_texts()
    texts[key] = message.text
    save_texts(texts)
    await message.answer(f"✅ Текст для <b>{key}</b> обновлён.",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад",callback_data="change_fields")]]))
    await state.clear()