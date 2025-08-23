from aiogram import Router, F, types
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

import asyncio
from database.models import Studios
from logic.scrap_studios import update_all_studios
from database.orm_query import (
    orm_add_studio,
    orm_update_studio,
    orm_delete_studio,
    orm_get_studios,
    orm_get_studio,
    orm_get_studio_by_name,
)

admin_studios_router = Router()

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
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Стартовое меню ---
@admin_studios_router.message(F.text == "Редактировать Студии")
async def admin_studios_menu(message: Message):
    await message.answer("Меню управления студиями:", reply_markup=get_admin_studios_kb())


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


# --- Список студий ---
STUDIOS_PER_PAGE = 8


def get_studios_keyboard(studios, page: int, total_pages: int):
    keyboard = [
        [InlineKeyboardButton(
            text=f"{'🆓' if studio.cost == 0 else '💳'} {(studio.name).capitalize()}",
            callback_data=f"studio_detail:{studio.id}"
        )]
        for studio in studios
    ]

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⏮ Назад", callback_data=f"studios_page:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="⏭ Далее", callback_data=f"studios_page:{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@admin_studios_router.callback_query(F.data == "list_studios")
async def list_studios(message_or_callback, session, page: int = 1):
    PAGE_SIZE = 8
    offset = (page - 1) * PAGE_SIZE
    studios = (await session.execute(select(Studios).offset(offset).limit(PAGE_SIZE))).scalars().all()
    total = (await session.execute(select(func.count(Studios.id)))).scalar_one()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    if not studios:
        await message_or_callback.answer("Студии не найдены")
        return

    text = "Список студий:\n\n" + "\n".join([f"▫️ {studio.name.capitalize()}" for studio in studios])
    keyboard = get_studios_keyboard(studios, page, total_pages)

    if isinstance(message_or_callback, types.CallbackQuery):
        try:
            await message_or_callback.message.edit_text(text, reply_markup=keyboard, ParseMode='HTML')
        except Exception:
            await message_or_callback.message.answer(text, reply_markup=keyboard, ParseMode='HTML')
    else:
        await message_or_callback.answer(text, reply_markup=keyboard, ParseMode='HTML')


@admin_studios_router.callback_query(F.data.startswith("studios_page:"))
async def studios_page_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await list_studios(callback, session, page)


@admin_studios_router.callback_query(F.data.startswith("studio_detail:"))
async def studio_detail_handler(callback: types.CallbackQuery, session: AsyncSession):
    studio_id = int(callback.data.split(":")[1])
    studio = await orm_get_studio(session, studio_id)
    if not studio:
        await callback.answer("Студия не найдена", show_alert=True)
        return

    caption = f"{studio.name}"
    description = (
        f"👨‍🏫 Преподаватель: {studio.teacher or '—'}\n"
        f"💰 Стоимость: {studio.cost} руб.\n"
        f"🎂 Возраст: {studio.age}\n"
        f"🏷 Категория: {studio.category}\n"
        f"️⏱️ Обновлено {studio.updated} \n\n"
        f"ℹ️ {studio.description}"


    )

    if studio.img:
        try:
            await callback.message.answer_photo(studio.img, caption=caption, ParseMode='HTML')
        except Exception:
            await callback.message.answer(caption, ParseMode='HTML')
    else:
        await callback.message.answer(caption, ParseMode='HTML')

    await callback.message.answer(description)
    await callback.answer()


# --- Обновить все студии ---
@admin_studios_router.callback_query(F.data == "update_all_studios")
async def update_all_studios_handler(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer("🔄 Запускаю обновление студий, подождите...\nПримерное время обновления ~3 минуты")
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
