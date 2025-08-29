import asyncio

from aiogram import Router, F, types, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import or_f,Command

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from sqlalchemy.ext.asyncio import AsyncSession


from database import orm_query
from database.orm_query import (
    orm_add_event, orm_update_event, orm_delete_event,
    orm_get_events, orm_get_event_by_name
)
from logic.scrap_events import update_all_events, find_age_limits
from handlers.notification import notify_subscribers
from filter.filter import check_message, IsAdmin, ChatTypeFilter

servises_router = Router()
servises_router.message.filter(ChatTypeFilter(['private']))

def get_services_kb():
    buttons = [
        [InlineKeyboardButton(text="Документы", callback_data="show_documents")],
        [InlineKeyboardButton(text="Верификация участника кружков", url="http://uslugi.mosreg.ru")],
        [InlineKeyboardButton(text="Аренда Помещений (прайс)", url="https://дк-яуза.рф/upload/iblock/d14/6tpgb3m5717z0eaxa0ghbx386zvtgnut.pdf")],
        [InlineKeyboardButton(text="Обратная свясь",
                              url="https://forms.mkrf.ru/e/2579/xTPLeBU7/?ap_orgcode=640160132")],
        [InlineKeyboardButton(text="🏠 В Главное меню", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@servises_router.message(or_f(Command('servises'),(F.text == "💼Услуги")))
async def notification(message: types.Message, session: AsyncSession):
    await message.answer("Список дополнительных услуг", reply_markup=get_services_kb())