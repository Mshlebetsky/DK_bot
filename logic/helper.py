from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
import re

def is_valid_url(url: str) -> bool:
    """Простая проверка, что ссылка похожа на валидную картинку"""
    if not url:
        return False
    pattern = r"^https?:\/\/.*\.(jpg|jpeg|png|gif|webp)(\?.*)?$"
    return re.match(pattern, url, re.IGNORECASE) is not None


async def send_photo_with_text(
    bot: Bot,
    chat_id: int,
    photo: str,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML"
):
    """
    Универсальный хелпер:
    - если есть валидный URL фото → отправляем фото
    - если URL битый или Telegram его не принимает → шлём только текст
    """
    if photo and is_valid_url(photo):
        try:
            if len(text) <= 1024:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    reply_markup=reply_markup
                )
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode
                )
            return
        except Exception as e:
            # fallback если Telegram не смог загрузить
            print(f"⚠ Ошибка загрузки фото {photo}: {e}")

    # если фото нет или оно битое
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def send_entity_card(callback, entity, back_cb: str, detail_cb: str):
    """
    Универсальный показ карточки сущности (студия, событие, новость).

    :param callback: объект CallbackQuery
    :param entity: объект SQLAlchemy (Studios, Events, News)
    :param back_cb: callback_data для кнопки "Назад"
    :param detail_cb: callback_data для кнопки "Подробнее"
    """

    # Название и обрезанный текст
    text = f"<b>{entity.name}</b>\n\n"
    description = (entity.description or "Нет описания")
    short_desc = description[:500] + ("…" if len(description) > 500 else "")
    text += short_desc

    # Кнопки
    buttons = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)],
        [InlineKeyboardButton(text="ℹ Подробнее", callback_data=detail_cb)]
    ]
    if getattr(entity, "link", None):  # если есть ссылка
        if entity.link:
            buttons.append([InlineKeyboardButton(text="🔗 Перейти", url=entity.link)])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Отправляем фото, если есть
    if getattr(entity, "img", None) and entity.img:
        try:
            await callback.message.answer_photo(
                photo=entity.img,
                caption=text[:1024],  # Telegram ограничение
                reply_markup=kb
            )
        except Exception as e:
            print(f"⚠ Ошибка загрузки фото: {e}")
            await callback.message.answer(text, reply_markup=kb)
    else:
        await callback.message.answer(text, reply_markup=kb)

    await callback.answer()


async def send_entity_full(callback, entity, back_cb: str):
    """
    Показывает полное описание сущности
    """
    text = f"<b>{entity.name}</b>\n\n{entity.description or 'Нет описания'}"

    buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)]]
    if getattr(entity, "link", None):
        if entity.link:
            buttons.append([InlineKeyboardButton(text="🔗 Перейти", url=entity.link)])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()
