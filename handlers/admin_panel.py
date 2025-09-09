from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from aiogram.filters import Command, or_f
from aiogram import Router, types, F, Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from filter.filter import ChatTypeFilter, IsAdmin, IsEditor, check_user, get_user_role

from data.text import admin_welcome
from database.models import Admin
from filter.filter import IsSuperAdmin
from handlers.notification import send_event_reminders, logger, notify_all_users
from logic.cmd_list import private

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


admin_router = Router()
admin_router.message.filter(ChatTypeFilter(['private']),IsAdmin())


admin_manage_router = Router()
admin_manage_router.message.filter(or_f(IsSuperAdmin(),IsEditor()))

@admin_manage_router.message(Command('check'))
async def check_(message: types.Message, bot: Bot, session: AsyncSession):
    if await IsSuperAdmin()(message, bot=bot):
        await message.answer("Вы супер админ")
    elif await IsEditor()(message, session=session):
        await message.answer("Вы редактор")
    else:
        await message.answer("Вы обычный пользователь")


async def admin_panel_menu(user: types.User, bot: Bot, new_session: AsyncSession):
    role = await get_user_role(user.id, new_session)

    buttons = [
        [InlineKeyboardButton(text='Редактировать Афишу', callback_data="edit_events_panel")],
        [InlineKeyboardButton(text='Редактировать Студии', callback_data="edit_studios_panel")],
        [InlineKeyboardButton(text='Редактировать Новости', callback_data="edit_news_panel")]
    ]

    if role == 'super_admin':
        buttons.append([InlineKeyboardButton(text='Редактировать Администраторов', callback_data="manage_editors")])
        buttons.append([InlineKeyboardButton(text="Отправить всем!📢", callback_data='notify_all_start')])

    buttons.append([InlineKeyboardButton(text="🏠 В Главное меню", callback_data='main_menu')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@admin_manage_router.message(Command('admin'))
async def admin_panel(message: types.Message, bot: Bot, session: AsyncSession):
    await message.answer(f'{admin_welcome}', reply_markup=await admin_panel_menu(message.from_user, bot, session))


@admin_manage_router.callback_query(F.data == 'admin_panel')
async def admin_menu2(callback : CallbackQuery, bot: Bot, session: AsyncSession):
    await callback.message.edit_text(admin_welcome, reply_markup=await admin_panel_menu(callback.from_user, bot, session))




@admin_router.callback_query(F.data == "manage_editors")
async def manage_editors(callback: CallbackQuery, session: AsyncSession):
    editors = (await session.execute(select(Admin))).scalars().all()
    text = "🛠 Управление редакторами:\n\n"
    for ed in editors:
        text += f"• {ed.user_id} ({ed.role})\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить редактора", callback_data="add_editor")],
        [InlineKeyboardButton(text="➖ Удалить редактора", callback_data="remove_editor")],
        [InlineKeyboardButton(text="🏠 Назад", callback_data="admin_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)


class EditorFSM(StatesGroup):
    add_id = State()
    remove_id = State()


@admin_router.callback_query(F.data == "add_editor")
async def add_editor(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте ID пользователя, которого хотите назначить редактором.")
    # переводим в состояние FSM (надо завести стейт-машину)
    await state.set_state(EditorFSM.add_id)


@admin_router.callback_query(F.data == "remove_editor")
async def remove_editor(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте ID пользователя, которого хотите удалить из редакторов.")
    # тоже FSM
    await state.set_state(EditorFSM.remove_id)


@admin_router.message(EditorFSM.add_id)
async def editor_add_handler(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        user_id = int(message.text)
        session.add(Admin(user_id=user_id, role="editor"))
        await session.commit()
        await message.answer(f"✅ Пользователь {user_id} назначен редактором")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()



@admin_router.message(EditorFSM.remove_id)
async def editor_remove_handler(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        user_id = int(message.text)
        await session.execute(delete(Admin).where(Admin.user_id == user_id))
        await session.commit()
        await message.answer(f"✅ Пользователь {user_id} удален из редакторов")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()



@admin_router.message(Command('set_menu'))
async def set_menu(message: types.Message, bot: Bot):
    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())


@admin_router.message(Command('send_reminders'))
async def send_reminders(message: types.Message, session: AsyncSession, bot: Bot):
    await send_event_reminders(bot, session)
    await message.answer("Тестовые напоминания отправлены!")


class NotifyAll(StatesGroup):
    text = State()
    choose_img = State()
    img = State()
    confirm = State()


@admin_router.message(Command("notify_all_users"))
async def send_reminders(message: types.Message):
    await message.answer(
        "Отправить уведомление всем пользователям?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="notify_all_start")],
            [InlineKeyboardButton(text="Нет", callback_data="main_menu")]
        ])
    )

@admin_router.callback_query(F.data == "notify_all_start")
async def notify_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(NotifyAll.text)
    await callback.message.answer("Введите текст уведомления:")
    await callback.answer()


@admin_router.message(NotifyAll.text)
async def notify_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(NotifyAll.choose_img)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить фото", callback_data="notify_add_img")],
        [InlineKeyboardButton(text="❌ Без фото", callback_data="notify_no_img")]
    ])

    await message.answer("Хотите прикрепить фото?", reply_markup=kb)


@admin_router.callback_query(F.data == "notify_add_img")
async def notify_add_img(callback: CallbackQuery, state: FSMContext):
    await state.set_state(NotifyAll.img)
    await callback.message.answer("Отправьте ссылку (URL) на изображение:")
    await callback.answer()


@admin_router.callback_query(F.data == "notify_no_img")
async def notify_no_img(callback: CallbackQuery, state: FSMContext):
    await state.update_data(img=None)
    await show_preview(callback.message, state)
    await callback.answer()


@admin_router.message(NotifyAll.img)
async def notify_img(message: types.Message, state: FSMContext):
    await state.update_data(img=message.text)
    await show_preview(message, state)


async def show_preview(message_or_callback, state: FSMContext):
    data = await state.get_data()
    text = data["text"]
    img = data.get("img")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="notify_confirm")],
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="notify_all_start")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")]
    ])
    try:
        if img:
            await message_or_callback.answer_photo(img, caption=f"{text}\n\nОтправить?", reply_markup=kb)
        else:
            await message_or_callback.answer(f"{text}\n\nОтправить?", reply_markup=kb)
    except Exception as e:
        logger.warning(f"❌ Не удалось отправить : {e}")
        await message_or_callback.answer(f"❌ Ошибка: {e}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Попробовать ещё раз", callback_data="notify_all_start")],
            [InlineKeyboardButton(text="🏠 В Главное меню", callback_data='main_menu')]
        ]))
    await state.set_state(NotifyAll.confirm)


@admin_router.callback_query(F.data == "notify_confirm")
async def notify_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession):
    data = await state.get_data()
    await state.clear()

    text = data["text"]
    img = data.get("img")

    # await broadcast_to_all_users(bot, session, text, img)
    await notify_all_users(bot, session, text, img)

    await callback.message.answer("✅ Уведомление отправлено!")
    await callback.answer()


