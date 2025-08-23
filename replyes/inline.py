from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_callback_btns(
        *,
        btns: dict[str, str],
        sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()

    for text, data in btns.items():
        keyboard.add(InlineKeyboardButton(text=text, callback_data=data))

    return keyboard.adjust(*sizes).as_markup()


def get_url_btns(
        *,
        btns: dict[str, str],
        sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()

    for text, url in btns.items():
        keyboard.add(InlineKeyboardButton(text=text, url=url))

    return keyboard.adjust(*sizes).as_markup()


# Создать микс из CallBack и URL кнопок
def get_inlineMix_btns(
        *,
        btns: dict[str, str],
        sizes: tuple[int] = (2,)):
    keyboard = InlineKeyboardBuilder()

    for text, value in btns.items():
        if '://' in value:
            keyboard.add(InlineKeyboardButton(text=text, url=value))
        else:
            keyboard.add(InlineKeyboardButton(text=text, callback_data=value))

    return keyboard.adjust(*sizes).as_markup()


from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def get_studios_keyboard(studios, page: int, total: int):
    kb = InlineKeyboardBuilder()

    for studio in studios:
        kb.button(text=studio.name, callback_data=f"studio_{studio.id}")

    # Пагинация
    if page > 0:
        kb.button(text="⬅️ Назад", callback_data=f"studios_page_{page-1}")
    if (page + 1) * 5 < total:
        kb.button(text="➡️ Вперёд", callback_data=f"studios_page_{page+1}")

    kb.adjust(1)
    return kb.as_markup()


def get_studio_detail_keyboard(studio_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Назад к списку", callback_data="studios_page_0")
    return kb.as_markup()


def get_pagination_keyboard(page: int, total: int):
    kb = InlineKeyboardBuilder()
    if page > 0:
        kb.button(text="⬅️", callback_data=f"studios_page_{page-1}")
    if (page + 1) * 5 < total:
        kb.button(text="➡️", callback_data=f"studios_page_{page+1}")
    return kb.as_markup()
