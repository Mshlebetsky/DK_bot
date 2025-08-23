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