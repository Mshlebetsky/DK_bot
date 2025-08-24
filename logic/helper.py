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
from aiogram import types

async def send_item_card(
    callback: types.CallbackQuery,
    item_id: int,
    page: int,
    title: str,
    short_text: str,
    img: str | None,
    detail_callback: str,
):
    """
    Универсальная отправка карточки (с краткой инфой).
    Добавляет кнопку назад (удалить карточку) и подробнее.
    """
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"close_card:{callback.message.message_id}:{page}"),
        InlineKeyboardButton(text="ℹ Подробнее", callback_data=f"{detail_callback}:{item_id}:{page}")
    ]])

    if img:
        try:
            await callback.message.answer_photo(
                img,
                caption=f"<b>{title}</b>\n\n{short_text}",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                f"<b>{title}</b>\n\n{short_text}",
                reply_markup=kb,
                parse_mode="HTML"
            )
    else:
        await callback.message.answer(
            f"<b>{title}</b>\n\n{short_text}",
            reply_markup=kb,
            parse_mode="HTML"
        )


async def close_item_card(callback: types.CallbackQuery):
    """
    Универсальный обработчик кнопки "Назад" для удаления карточки
    """
    _, list_msg_id, page = callback.data.split(":")
    try:
        await callback.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
    except Exception:
        pass
    await callback.answer()
