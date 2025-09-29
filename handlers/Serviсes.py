import logging
from aiogram import Router, F, types, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from filter.filter import ChatTypeFilter
from logic.helper import get_text




# ================== ЛОГИРОВАНИЕ ==================

logger = logging.getLogger(__name__)

# ================== РОУТЕР ==================


services_router = Router()
services_router.message.filter(ChatTypeFilter(["private"]))


# ---------- Keyboards ----------
def get_services_keyboard() -> InlineKeyboardMarkup:
    """Главное меню услуг"""
    buttons = [
        [InlineKeyboardButton(text="Верификация участника кружков", url="http://uslugi.mosreg.ru")],
        [InlineKeyboardButton(text="Аренда помещений", callback_data="rent_menu")],
        [InlineKeyboardButton(
            text="Обратная связь",
            url="https://forms.mkrf.ru/e/2579/xTPLeBU7/?ap_orgcode=640160132"
        )],
        [InlineKeyboardButton(text="Расписание студий (кружков)", url="https://дк-яуза.рф/upload/rasp.docx")],
        [InlineKeyboardButton(text="🏠 В Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_rent_menu_keyboard(msg_id: int) -> InlineKeyboardMarkup:
    """Меню аренды помещений"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Большой зал", callback_data=f"big_hall_{msg_id}")],
        [InlineKeyboardButton(text="Малый зал", callback_data=f"small_hall_{msg_id}")],
        [InlineKeyboardButton(text="Бальный зал", callback_data=f"dance_hall_{msg_id}")],
        [InlineKeyboardButton(
            text="Аренда помещений (прайс)",
            url="https://дк-яуза.рф/upload/iblock/d14/6tpgb3m5717z0eaxa0ghbx386zvtgnut.pdf"
        )],
        [InlineKeyboardButton(text="Ссылка на сайт", url="https://дк-яуза.рф/prostranstva/")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="services")],
    ])


def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="rent_menu")]
    ])


# ---------- Handlers ----------
@services_router.message(Command("services"))
async def show_services(message: Message, session: AsyncSession) -> None:
    """Отображает список услуг"""
    logger.info("Пользователь %s запросил список услуг", message.from_user.id)
    await message.answer("Список дополнительных услуг", reply_markup=get_services_keyboard())


@services_router.callback_query(F.data == "rent_menu")
async def show_rent_menu(callback: CallbackQuery) -> None:
    """Меню аренды помещений"""
    logger.info("Открыто меню аренды пользователем %s", callback.from_user.id)
    try:
        await callback.message.edit_text(
            "Аренда помещений",
            reply_markup=get_rent_menu_keyboard(callback.message.message_id)
        )
    except Exception as e:
        logger.error("Ошибка при показе меню аренды: %s", e)
        await callback.message.answer("❌ Не удалось открыть меню аренды")


# --- Generic function for halls ---
async def show_hall(
    callback: CallbackQuery,
    bot: Bot,
    hall_name: str,
    msg_id: str,
    photos: list[str],
    description_text: str = "",
    extra_text: str = ""
) -> None:
    """Отображает зал с фото и описанием"""
    try:
        await bot.delete_message(callback.message.chat.id, int(msg_id))
        logger.debug("Удалено старое сообщение %s для зала %s", msg_id, hall_name)
    except Exception as e:
        logger.warning("Не удалось удалить сообщение %s: %s", msg_id, e)

    description = f"<b>{hall_name}</b>\n\n{description_text}"

    media_group = MediaGroupBuilder(caption=description)
    for photo in photos:
        media_group.add_photo(type="photo", media=photo)

    try:
        await callback.message.answer_media_group(media=media_group.build())
        await callback.message.answer(extra_text, reply_markup=get_back_keyboard())
        logger.info("Показан зал %s пользователю %s", hall_name, callback.from_user.id)
    except Exception as e:
        logger.error("Ошибка при показе зала %s: %s", hall_name, e)
        await callback.message.answer("❌ Не удалось загрузить фотографии")


# --- Halls ---
@services_router.callback_query(F.data.startswith("big_hall_"))
async def show_big_hall(callback: CallbackQuery, bot: Bot) -> None:

    await show_hall(
        callback,
        bot,
        hall_name="Большой Зал",
        msg_id=callback.data.split("_")[-1],
        photos=[
            "https://дк-яуза.рф/upload/iblock/e8e/9rghh0bjp38ly4r1y3r2mq5cuvgbinrb.JPG",
            "https://дк-яуза.рф/upload/iblock/823/sp566u4xoqrwnjrgsrdu3qu8kgon4b1u.JPG",
            "https://дк-яуза.рф/upload/iblock/cb9/0o2ej2atw4xysmb7wxy3w23pcn6pkd9l.JPG",
            "https://дк-яуза.рф/upload/iblock/27f/5rtlo69rtr9oc2xlqi96dv81k6lbbqk3.JPG",
            "https://дк-яуза.рф/upload/iblock/411/6w2d08uszkngv2x5fj0s1m5d4j6qap9x.JPG",
            "https://дк-яуза.рф/upload/iblock/2eb/b75klduuthr2exo96w3jjnamuv5n8xmn.jpg"
        ],
        description_text= get_text("big_hall"),
        extra_text=get_text("short_info")
    )


@services_router.callback_query(F.data.startswith("small_hall_"))
async def show_small_hall(callback: CallbackQuery, bot: Bot) -> None:

    await show_hall(
        callback,
        bot,
        hall_name="Малый Зал",
        msg_id=callback.data.split("_")[-1],
        photos=[
            "https://дк-яуза.рф/upload/iblock/ba6/xrmzvi87418sfqc38ll2ylfmwgyvg9e7.jpg",
            "https://дк-яуза.рф/upload/iblock/4dc/1sq4mqz0oizplwwbbvopk5x84gid0u1z.jpg",
            "https://дк-яуза.рф/upload/iblock/817/v80u79rcnzzo020ydtyzpfdad4dxqj40.jpg",
            "https://дк-яуза.рф/upload/iblock/15d/v4v6v1188sgy2e0hoptjwhsooap81nz5.jpg",
            "https://дк-яуза.рф/upload/iblock/e68/hi5g190n6w2hrp64t7t7i01oa3o2cwva.jpg",
            "https://дк-яуза.рф/upload/iblock/0aa/jmqkpac422l8422w8ychyitz32heazup.jpg"
        ],
        description_text=get_text("small_hall"),
        extra_text=get_text("short_info")
    )


@services_router.callback_query(F.data.startswith("dance_hall_"))
async def show_dance_hall(callback: CallbackQuery, bot: Bot) -> None:


    await show_hall(
        callback,
        bot,
        hall_name="Бальный Зал",
        msg_id=callback.data.split("_")[-1],
        photos=[
            "https://дк-яуза.рф/upload/iblock/3df/72pwgvfgf8vynkz1mqrqc19t2tjdkac0.JPG",
            "https://дк-яуза.рф/upload/iblock/7d1/o6p930nom2fqpn3pzh3d9dndd9ml0qji.JPG",
            "https://дк-яуза.рф/upload/iblock/a80/ntrw4n887g0rh2twaiykc0fip252onvs.JPG",
            "https://дк-яуза.рф/upload/iblock/ae1/yg5rlae0o0fb8tfxrr2t1wkymtwlp6nd.JPG"
        ],
        description_text=get_text("ballroom"),
        extra_text=get_text("short_info")
    )
