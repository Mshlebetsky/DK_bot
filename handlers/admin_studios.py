import asyncio

from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import or_f,Command

from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import (
    orm_add_studio,
    orm_update_studio,
    orm_delete_studio,
    orm_get_studios,
    orm_get_studio_by_name,
)

from logic.scrap_studios import update_all_studios
from filter.filter import IsAdmin, ChatTypeFilter


admin_studios_router = Router()
admin_studios_router.message.filter(ChatTypeFilter(['private']),IsAdmin())


# --- FSM ---
class AddStudioFSM(StatesGroup):
    name = State()
    description = State()
    teacher = State()
    cost = State()
    age = State()
    category = State()
    qr_img = State()
    img = State()


class EditStudioFSM(StatesGroup):
    id = State()
    field = State()
    value = State()


class DeleteStudioFSM(StatesGroup):
    id = State()


# --- Клавиатуры ---
def get_admin_studios_kb():
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить студию", callback_data="add_studio")],
        [InlineKeyboardButton(text="✏️ Изменить студию", callback_data="edit_studio")],
        [InlineKeyboardButton(text="🗑 Удалить студию", callback_data="delete_studio")],
        [InlineKeyboardButton(text="📋 Список студий", callback_data="list_studios")],
        [InlineKeyboardButton(text="🔄 Обновить все студии", callback_data="update_all_studios")],
        [InlineKeyboardButton(text="🛠В панель администратора", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Стартовое меню ---
@admin_studios_router.message(or_f((F.text == "Редактировать Студии"),Command('edit_studios')))
async def admin_studios_menu(message: Message):
    await message.answer("Меню управления студиями:", reply_markup=get_admin_studios_kb())

@admin_studios_router.callback_query(F.data == 'edit_studios_panel')
async def admin_events_menu(callback: CallbackQuery):
    await callback.message.edit_text("Меню управления студиями:", reply_markup=get_admin_studios_kb())


# --- Добавление студии ---
@admin_studios_router.callback_query(F.data == "add_studio")
async def add_studio_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddStudioFSM.name)
    await callback.message.answer("Введите название студии:")


@admin_studios_router.message(AddStudioFSM.name)
async def add_studio_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddStudioFSM.description)
    await message.answer("Введите описание студии:")


@admin_studios_router.message(AddStudioFSM.description)
async def add_studio_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddStudioFSM.teacher)
    await message.answer("Введите имя преподавателя (или '-' если нет):")


@admin_studios_router.message(AddStudioFSM.teacher)
async def add_studio_teacher(message: Message, state: FSMContext):
    await state.update_data(teacher=message.text)
    await state.set_state(AddStudioFSM.cost)
    await message.answer("Введите стоимость, если бесплатно, то поставьте 0:")


@admin_studios_router.message(AddStudioFSM.cost)
async def add_studio_cost(message: Message, state: FSMContext):
    try:
        cost = int(message.text)
    except ValueError:
        await message.answer("Стоимость должна быть числом. Повторите ввод:")
        return
    await state.update_data(cost=cost)
    await state.set_state(AddStudioFSM.age)
    await message.answer("Введите возрастную категорию (например, '6-12'):")


@admin_studios_router.message(AddStudioFSM.age)
async def add_studio_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(AddStudioFSM.category)
    await message.answer("Введите категорию студии:")


@admin_studios_router.message(AddStudioFSM.category)
async def add_studio_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text.lower())
    await state.set_state(AddStudioFSM.qr_img)
    await message.answer("Отправьте ссылку на QR-картинку (или '-' если нет):")


@admin_studios_router.message(AddStudioFSM.qr_img)
async def add_studio_qr_img(message: Message, state: FSMContext):
    qr_img = None if message.text == "-" else message.text
    await state.update_data(qr_img=qr_img)
    await state.set_state(AddStudioFSM.img)
    await message.answer("Отправьте ссылку на изображение студии (или '-' если нет):")


@admin_studios_router.message(AddStudioFSM.img)
async def add_studio_img(message: Message, state: FSMContext, session: AsyncSession):
    img = None if message.text == "-" else message.text
    await state.update_data(img=img)
    data = await state.get_data()
    await orm_add_studio(session, data)
    await state.clear()
    await message.answer("✅ Студия успешно добавлена!", reply_markup=get_admin_studios_kb())


# --- Изменение студии ---
@admin_studios_router.callback_query(F.data == "edit_studio")
async def edit_studio_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    studios = await orm_get_studios(session)
    if not studios:
        await callback.message.answer("❌ Нет студий для изменения.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=st.name.lower(), callback_data=f"edit_studio_{st.id}")] for st in studios]
    )
    await callback.message.answer("Выберите студию для редактирования:", reply_markup=kb)


@admin_studios_router.callback_query(F.data.startswith("edit_studio_"))
async def edit_studio_choose(callback: CallbackQuery, state: FSMContext):
    studio_id = int(callback.data.split("_")[2])
    await state.set_state(EditStudioFSM.field)
    await state.update_data(id=studio_id)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Название", callback_data="field_name")],
            [InlineKeyboardButton(text="Описание", callback_data="field_description")],
            [InlineKeyboardButton(text="Преподаватель", callback_data="field_teacher")],
            [InlineKeyboardButton(text="Стоимость", callback_data="field_cost")],
            [InlineKeyboardButton(text="Возраст", callback_data="field_age")],
            [InlineKeyboardButton(text="Категория", callback_data="field_category")],
            [InlineKeyboardButton(text="QR", callback_data="field_qr_img")],
            [InlineKeyboardButton(text="Изображение", callback_data="field_img")],
        ]
    )
    await callback.message.answer("Выберите поле для изменения:", reply_markup=kb)


@admin_studios_router.callback_query(F.data.startswith("field_"), EditStudioFSM.field)
async def edit_studio_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("field_", "")
    await state.update_data(field=field)
    await state.set_state(EditStudioFSM.value)
    await callback.message.answer(f"Введите новое значение для поля {field}:")


@admin_studios_router.message(EditStudioFSM.value)
async def edit_studio_value(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    field = data["field"]
    value = message.text
    studio_id = data["id"]

    if field == "cost":
        try:
            value = int(value)
        except ValueError:
            await message.answer("Стоимость должна быть числом. Повторите ввод:")
            return

    await orm_update_studio(session, studio_id, field, value)
    await state.clear()
    await message.answer("✅ Студия успешно изменена!", reply_markup=get_admin_studios_kb())


# --- Удаление студии ---
@admin_studios_router.callback_query(F.data == "delete_studio")
async def delete_studio_start(callback: CallbackQuery, session: AsyncSession):
    studios = await orm_get_studios(session)
    if not studios:
        await callback.message.answer("❌ Нет студий для удаления.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=st.name.lower(), callback_data=f"delete_studio_{st.id}")] for st in studios]
    )
    await callback.message.answer("Выберите студию для удаления:", reply_markup=kb)


@admin_studios_router.callback_query(F.data.startswith("delete_studio_"))
async def delete_studio_confirm(callback: CallbackQuery, session: AsyncSession):
    studio_id = int(callback.data.split("_")[2])
    await orm_delete_studio(session, studio_id)
    await callback.message.answer("🗑 Студия удалена!", reply_markup=get_admin_studios_kb())



# --- Обновить все студии ---
@admin_studios_router.callback_query(F.data == "update_all_studios")
async def update_all_studios_handler(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer("🔄 Запускаю обновление студий, пожалуйста подождите...\nПримерное время обновления ~3 минуты")
    try:
        data, log_text = await asyncio.to_thread(update_all_studios)
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при вызове парсера: {e}")
        return

    updated, added = 0, 0
    for name, values in data.items():
        try:
            description, cost, age, img, qr_img, teacher, category = values
        except ValueError:
            await callback.message.answer(f"⚠️ Пропущена студия {name}: неверный формат данных")
            continue

        studio = await orm_get_studio_by_name(session, name)
        if studio:
            await orm_update_studio(session, studio.id, "description", description)
            await orm_update_studio(session, studio.id, "cost", int(cost))
            await orm_update_studio(session, studio.id, "age", age)
            await orm_update_studio(session, studio.id, "img", img)
            await orm_update_studio(session, studio.id, "qr_img", qr_img)
            await orm_update_studio(session, studio.id, "teacher", teacher)
            await orm_update_studio(session, studio.id, "category", category)
            updated += 1
        else:
            new_data = {
                "name": name,
                "description": description,
                "teacher": teacher,
                "cost": int(cost),
                "age": age,
                "category": category,
                "qr_img": qr_img,
                "img": img,
            }
            await orm_add_studio(session, new_data)
            added += 1

    await callback.message.answer(
        f"{log_text}\n\n"
        f"🔄 Обновлено: {updated}\n"
        f"➕ Добавлено: {added}",
        reply_markup=get_admin_studios_kb()
    )