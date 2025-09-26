import json
from pathlib import Path

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


def Big_litter_start(s: str):
    if s[0] == '«':
        return f'«{s[1:].capitalize()}'
    elif s[0] ==  '\"':
        return f'\"{s[1:].capitalize()}'
    else:
        return s.capitalize()


async def safe_edit_message(message: types.Message, text: str, kb: InlineKeyboardMarkup) -> None:
    """
    Универсальное редактирование сообщения.
    Если это текст — edit_text.
    Если это фото/видео с подписью — edit_caption.
    Если редактирование невозможно — удаляет и шлёт новое.
    """
    try:
        if message.text:  # обычное текстовое сообщение
            await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        elif message.caption:  # сообщение с подписью (фото, видео и т.д.)
            await message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.delete()
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        from handlers.Event_list import logger
        logger.warning("safe_edit_message: %s", e)
        try:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
        except Exception as inner_e:
            logger.error("Не удалось отправить новое сообщение: %s", inner_e)


TEXTS_PATH = Path("texts.json")


def load_texts():
    with open(TEXTS_PATH, encoding="utf-8") as f:
        return json.load(f)

def get_text(key: str) -> str:
    texts = load_texts()
    return texts.get(key, "")

def save_texts(data: dict):
    with open(TEXTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)