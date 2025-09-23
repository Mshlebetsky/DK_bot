import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import or_f, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import (
    orm_add_studio,
    orm_update_studio,
    orm_delete_studio,
    orm_get_studios,
    orm_get_studio_by_name, orm_get_studio,
)
from logic.helper import Big_litter_start
from logic.scrap_studios import update_all_studios
from filter.filter import IsSuperAdmin, IsEditor

# ================== ЛОГИРОВАНИЕ ==================

logger = logging.getLogger(__name__)

# ================== РОУТЕР ==================


admin_studios_router = Router()
admin_studios_router.message.filter(or_f(IsSuperAdmin(), IsEditor()))


# --- FSM States ---
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


# --- Keyboards ---
def get_admin_studios_kb() -> InlineKeyboardMarkup:
    """Главное меню управления студиями"""
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить студию", callback_data="add_studio")],
        [InlineKeyboardButton(text="✏️ Изменить студию", callback_data="edit_studio")],
        [InlineKeyboardButton(text="🗑 Удалить студию", callback_data="delete_studio")],
        [InlineKeyboardButton(text="🔄 Обновить все студии", callback_data="update_all_studios")],
        # [InlineKeyboardButton(text="Cинхронизировать всё", callback_data="delete_all_unlocked")],
        [InlineKeyboardButton(text="🛠 В панель администратора", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


PER_PAGE = 10  # количество студий на страницу

def get_studios_keyboard(studios, page: int = 0):

    """Возвращает inline-клавиатуру со студиями по страницам"""

    studios = sorted(studios, key=lambda s: s.name.lower())

    builder = InlineKeyboardBuilder()
    start = page * PER_PAGE
    end = start + PER_PAGE
    for st in studios[start:end]:
        builder.button(text=(Big_litter_start(st.name) if st.title =='' else st.title), callback_data=f"edit_studio_{st.id}")
    builder.button(text="🛠В меню управления", callback_data=f"edit_studios_panel")
    builder.adjust(1)

    # пагинация
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"studios_page_{page-1}")
    if end < len(studios):
        builder.button(text="Вперёд ➡️", callback_data=f"studios_page_{page+1}")

    return builder.as_markup()


def get_delete_studios_keyboard(studios, page: int = 0):
    """
    Формирует inline-клавиатуру для удаления студий с пагинацией
    """
    studios = sorted(studios, key=lambda s: s.name.lower())

    builder = InlineKeyboardBuilder()
    start = page * PER_PAGE
    end = start + PER_PAGE
    builder.button(text="🔥Удалить всё, кроме защищенных", callback_data=f"delete_all_studios")
    for st in studios[start:end]:
        builder.button(
            text=f"🗑 {st.name}",
            callback_data=f"delete_studio_{st.id}"
        )
    builder.button(text="В меню управления", callback_data=f"edit_studios_panel")
    builder.adjust(1)

    # Кнопки пагинации
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"delete_page_{page-1}")
    if end < len(studios):
        builder.button(text="Вперёд ➡️", callback_data=f"delete_page_{page+1}")

    return builder.as_markup()

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[

        InlineKeyboardButton(text="Назад в меню управления",callback_data="edit_studios_panel")
    ]])


# --- Admin Panel ---
@admin_studios_router.message(Command("edit_studios"))
async def admin_studios_menu(message: Message):
    """Вывод панели управления студиями"""
    logger.info("Открыто меню управления студиями (user_id=%s)", message.from_user.id)
    await message.answer("Меню управления студиями:", reply_markup=get_admin_studios_kb())


@admin_studios_router.callback_query(F.data == "edit_studios_panel")
async def admin_studios_panel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    logger.info("Переход в меню управления студиями (user_id=%s)", callback.from_user.id)
    await callback.message.edit_text("Меню управления студиями:", reply_markup=get_admin_studios_kb())


# --- Add Studio ---
@admin_studios_router.callback_query(F.data == "add_studio")
async def add_studio_start(callback: CallbackQuery, state: FSMContext):
    logger.info("Начало добавления студии (user_id=%s)", callback.from_user.id)
    await state.set_state(AddStudioFSM.name)
    await callback.message.answer("Введите название студии:", reply_markup=back_kb())


@admin_studios_router.message(AddStudioFSM.name)
async def add_studio_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    logger.debug("Название студии: %s", message.text)
    await state.set_state(AddStudioFSM.description)
    await message.answer("Введите описание студии:", reply_markup=back_kb())


@admin_studios_router.message(AddStudioFSM.description)
async def add_studio_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    logger.debug("Описание студии добавлено")
    await state.set_state(AddStudioFSM.teacher)
    await message.answer("Введите имя преподавателя (или '-' если нет):", reply_markup=back_kb())


@admin_studios_router.message(AddStudioFSM.teacher)
async def add_studio_teacher(message: Message, state: FSMContext):
    await state.update_data(teacher=message.text)
    logger.debug("Преподаватель: %s", message.text)
    await state.set_state(AddStudioFSM.cost)
    await message.answer("Введите стоимость (0 если бесплатно):", reply_markup=back_kb())


@admin_studios_router.message(AddStudioFSM.cost)
async def add_studio_cost(message: Message, state: FSMContext):
    try:
        cost = int(message.text)
        await state.update_data(cost=cost)
        logger.debug("Стоимость: %d", cost)
    except ValueError:
        logger.warning("Неверный ввод стоимости: %s", message.text)
        await message.answer("❌ Стоимость должна быть числом. Повторите ввод:")
        return

    await state.set_state(AddStudioFSM.age)
    await message.answer("Введите возрастную категорию (например, '6-12'):", reply_markup=back_kb())


@admin_studios_router.message(AddStudioFSM.age)
async def add_studio_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    logger.debug("Возраст: %s", message.text)
    await state.set_state(AddStudioFSM.category)
    await message.answer("Введите категорию студии:", reply_markup=back_kb())


@admin_studios_router.message(AddStudioFSM.category)
async def add_studio_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text.lower())
    logger.debug("Категория: %s", message.text.lower())
    await state.set_state(AddStudioFSM.qr_img)
    await message.answer("Отправьте ссылку на QR-картинку (или '-' если нет):", reply_markup=back_kb())


@admin_studios_router.message(AddStudioFSM.qr_img)
async def add_studio_qr_img(message: Message, state: FSMContext):
    qr_img = None if message.text == "-" else message.text
    await state.update_data(qr_img=qr_img)
    logger.debug("QR-img: %s", qr_img)
    await state.set_state(AddStudioFSM.img)
    await message.answer("Отправьте ссылку на изображение студии (или '-' если нет):", reply_markup=back_kb())


@admin_studios_router.message(AddStudioFSM.img)
async def add_studio_img(message: Message, state: FSMContext, session: AsyncSession):
    img = None if message.text == "-" else message.text
    await state.update_data(img=img)
    data = await state.get_data()

    try:
        await orm_add_studio(session, data)
        logger.info("Студия добавлена: %s", data.get("title"))
        await message.answer("✅ Студия успешно добавлена!", reply_markup=get_admin_studios_kb())
    except Exception as e:
        logger.exception("Ошибка при добавлении студии: %s", e)
        await message.answer("❌ Ошибка при добавлении студии.")
    finally:
        await state.clear()


# --- Edit Studio ---
@admin_studios_router.callback_query(F.data == "edit_studio")
async def edit_studio_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    studios = await orm_get_studios(session)
    if not studios:
        await callback.message.answer("❌ Нет студий для изменения.")
        return

    # сохраняем список студий в состояние, чтобы при листании не ходить в БД
    await state.update_data(studios=[{"id": s.id, "name": s.name} for s in studios])

    kb = get_studios_keyboard(studios, page=0)
    await callback.message.answer("Выберите студию для редактирования:", reply_markup=kb)


@admin_studios_router.callback_query(F.data.startswith("studios_page_"))
async def studios_page(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    studios = [type("Obj", (), s) for s in data["studios"]]  # превращаем dict обратно в объекты
    page = int(callback.data.split("_")[-1])
    kb = get_studios_keyboard(studios, page=page)
    await callback.message.edit_reply_markup(reply_markup=kb)


@admin_studios_router.callback_query(F.data.startswith("edit_studio_"))
async def edit_studio_choose(callback: CallbackQuery, state: FSMContext):
    studio_id = int(callback.data.split("_")[2])
    await state.update_data(id=studio_id)
    await state.set_state(EditStudioFSM.field)
    logger.info("Редактирование студии id=%s", studio_id)

    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"field_{field}")]
        for label, field in [
            ("Название", "title"),
            ("Описание", "description"),
            ("Преподаватель", "teacher"),
            ("Стоимость", "cost"),
            ("Возраст", "age"),
            ("Категория", "category"),
            ("QR", "qr_img"),
            ("Изображение", "img"),
            ("Запретить автоматическое изменение студии(да/нет)", "lock_changes"),
        ]
    ]

    # добавляем новую кнопку после генератора
    buttons.append(
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"edit_studio")]
    )
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer("Выберите поле для изменения:", reply_markup=kb)


@admin_studios_router.callback_query(F.data.startswith("field_"), EditStudioFSM.field)
async def edit_studio_field(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    field = callback.data.replace("field_", "")
    await state.update_data(field=field)
    await state.set_state(EditStudioFSM.value)

    data = await state.get_data()
    event = await orm_get_studio(session, data["id"])
    if field != 'title':
        current_value = getattr(event, field, None)
    else:
        if event.title == '':
            current_value = Big_litter_start(getattr(event, 'name', None))
        else:
            current_value = getattr(event, 'title', None)

    await callback.message.answer(f"Введите новое значение для поля {field}:\n"
                                  f"{'Введите - чтобы вернуть изначальное значение названия' if field == 'title' else ''}"
                                  f"\nЗначение сейчас:")
    await callback.message.answer(f"{current_value}")
    logger.debug("Выбранное поле для редактирования: %s", field)


@admin_studios_router.message(EditStudioFSM.value)
async def edit_studio_value(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    field, value, studio_id = data["field"], message.text, data["id"]


    if message.text == "-":
        value = ''
    if field == "lock_changes":
        value = value.lower() in ["да", "yes", 1, "True"]
    if field == "cost":
        try:
            value = int(value)
        except ValueError:
            logger.warning("Неверный ввод стоимости при редактировании: %s", message.text)
            await message.answer("❌ Стоимость должна быть числом. Повторите ввод:")
            return

    try:
        await orm_update_studio(session, studio_id, "lock_changes", True)
        await orm_update_studio(session, studio_id, field, value)
        logger.info("Обновлено поле %s у студии id=%s", field, studio_id)
        await message.answer("✅ Студия успешно изменена!", reply_markup=get_admin_studios_kb())
    except Exception as e:
        logger.exception("Ошибка при обновлении студии id=%s: %s", studio_id, e)
        await message.answer("❌ Ошибка при обновлении студии.")
    finally:
        await state.clear()


# --- Delete Studio ---
@admin_studios_router.callback_query(F.data == "delete_studio")
async def delete_studio_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    studios = await orm_get_studios(session)
    if not studios:
        await callback.message.answer("❌ Нет студий для удаления.")
        return

    # Сохраняем список в state
    await state.update_data(delete_studios=[{"id": s.id, "name": s.name} for s in studios])

    kb = get_delete_studios_keyboard(studios, page=0)
    await callback.message.answer("Выберите студию для удаления:", reply_markup=kb)


@admin_studios_router.callback_query(F.data.startswith("delete_page_"))
async def delete_studios_page(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    studios = [type("Obj", (), s) for s in data["delete_studios"]]  # восстанавливаем объекты
    page = int(callback.data.split("_")[-1])

    kb = get_delete_studios_keyboard(studios, page=page)
    await callback.message.edit_reply_markup(reply_markup=kb)



@admin_studios_router.callback_query(F.data.startswith("delete_studio_"))
async def delete_studio_confirm(callback: CallbackQuery, session: AsyncSession):
    studio_id = int(callback.data.split("_")[2])
    try:
        await orm_delete_studio(session, studio_id)
        logger.info("Удалена студия id=%s", studio_id)
        await callback.message.answer("🗑 Студия удалена!", reply_markup=get_admin_studios_kb())
    except Exception as e:
        logger.exception("Ошибка при удалении студии id=%s: %s", studio_id, e)
        await callback.message.answer("❌ Ошибка при удалении студии.")


# --- Update All Studios ---
@admin_studios_router.callback_query(F.data == "update_all_studios")
async def update_all_studios_handler(callback: CallbackQuery, session: AsyncSession):
    logger.info("Запуск обновления всех студий (user_id=%s)", callback.from_user.id)
    await callback.message.answer("🔄 Обновление студий... (~4 минуты)")

    try:
        data, log_text = await asyncio.to_thread(update_all_studios)
    except Exception as e:
        logger.exception("Ошибка при вызове парсера студий: %s", e)
        await callback.message.answer(f"❌ Ошибка при вызове парсера: {e}")
        return




    updated, added = 0, 0

    for name, values in data.items():
        try:
            description, cost, second_cost, age, img, qr_img, teacher, category = values
        except ValueError:
            logger.warning("Пропущена студия %s: неверный формат данных", name)
            await callback.message.answer(f"⚠️ Пропущена студия {name}: неверный формат данных")
            continue

        try:
            studios = await orm_get_studios(session)
            studio = await orm_get_studio_by_name(session, name)
            if studio:
                if (studio.lock_changes == False):
                    try:
                        await orm_delete_studio(session, studio.id)
                    except Exception as e:
                        logger.exception("Ошибка при массовом удалении студии id=%s: %s", studio.id, e)

                    new_data = {
                        "name": name,
                        "description": description,
                        "teacher": teacher,
                        "cost": int(cost),
                        "second_cost": second_cost,
                        "age": age,
                        "category": category,
                        "qr_img": qr_img,
                        "img": img,
                    }
                    await orm_add_studio(session, new_data)
                    updated += 1
                    logger.debug("Обновлена студия %s", name)
            else:
                new_data = {
                    "name": name,
                    "description": description,
                    "teacher": teacher,
                    "cost": int(cost),
                    "second_cost": second_cost,
                    "age": age,
                    "category": category,
                    "qr_img": qr_img,
                    "img": img,
                }
                await orm_add_studio(session, new_data)
                added += 1
                logger.debug("Добавлена новая студия %s", name)
        except Exception as e:
            logger.exception("Ошибка при обработке студии %s: %s", name, e)

    logger.info("Обновление студий завершено. Обновлено=%d, Добавлено=%d", updated, added)
    await callback.message.answer(
        f"{log_text}\n\n"
        f"🔄 Обновлено: {updated}\n"
        f"➕ Добавлено: {added}",
        reply_markup=get_admin_studios_kb()
    )


@admin_studios_router.callback_query(F.data == "delete_all_studios")
async def delete_all_studios_handler(callback: CallbackQuery, session: AsyncSession):

    try:
        studios = await orm_get_studios(session)
        deleted_count = 0

        for st in studios:
            # удаляем только если lock_changes == False (или None)
            if not getattr(st, "lock_changes", False):
                try:
                    await orm_delete_studio(session, st.id)
                    deleted_count += 1
                except Exception as e:
                    # логируем, но не прерываем цикл
                    logger.exception("Ошибка при массовом удалении студии id=%s: %s", st.id, e)

        await callback.message.answer(
            f"🗑 Удалено студий: {deleted_count}\n"
            f"✅ Защищённые остались на месте.", reply_markup=back_kb()
        )
    except:
        logger.info("Не удалось удалить студии")
