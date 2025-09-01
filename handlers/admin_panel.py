from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from aiogram.filters import  Command, or_f
from aiogram import Router, types, F
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from filter.filter import ChatTypeFilter, IsAdmin, check_message, get_admins_ids

from data.text import admin_welcome
from database.models import Admin
from filter.filter import IsSuperAdmin


admin_router = Router()
admin_router.message.filter(ChatTypeFilter(['private']),IsAdmin())


def admin_panel_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Редактировать Афишу', callback_data="edit_events_panel")],
        [InlineKeyboardButton(text='Редактировать Студии', callback_data="edit_studios_panel")],
        [InlineKeyboardButton(text='Редактировать Новости', callback_data="edit_news_panel")],
        [InlineKeyboardButton(text='Редактировать Администраторов', callback_data="manage_editors")],
        [InlineKeyboardButton(text="🏠 В Главное меню", callback_data='main_menu')]

    ])



@admin_router.message(or_f(Command('admin_panel'), (lambda msg: msg.text == "🛠Панель администратора")))
async def admin_panel(message: types.Message):
    await message.answer(f'{admin_welcome}', reply_markup=admin_panel_menu())


@admin_router.callback_query(F.data == 'admin_panel')
async def admin_menu2(callback : CallbackQuery):
    await callback.message.edit_text(admin_welcome, reply_markup=admin_panel_menu())


admin_manage_router = Router()


@admin_manage_router.callback_query(F.data == "manage_editors", IsSuperAdmin())
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


@admin_manage_router.callback_query(F.data == "add_editor", IsSuperAdmin())
async def add_editor(callback: CallbackQuery):
    await callback.message.answer("Отправьте ID пользователя, которого хотите назначить редактором.")
    # переводим в состояние FSM (надо завести стейт-машину)


@admin_manage_router.callback_query(F.data == "remove_editor", IsSuperAdmin())
async def remove_editor(callback: CallbackQuery):
    await callback.message.answer("Отправьте ID пользователя, которого хотите удалить из редакторов.")
    # тоже FSM


from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

class EditorFSM(StatesGroup):
    add_id = State()
    remove_id = State()


@admin_manage_router.message(EditorFSM.add_id, IsSuperAdmin())
async def editor_add_handler(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        user_id = int(message.text)
        session.add(Admin(user_id=user_id, role="editor"))
        await session.commit()
        await message.answer(f"✅ Пользователь {user_id} назначен редактором")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()


@admin_manage_router.message(EditorFSM.remove_id, IsSuperAdmin())
async def editor_remove_handler(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        user_id = int(message.text)
        await session.execute(delete(Admin).where(Admin.user_id == user_id))
        await session.commit()
        await message.answer(f"✅ Пользователь {user_id} удален из редакторов")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()
