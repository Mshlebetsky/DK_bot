from aiogram import Router, F, types, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from aiogram.utils.media_group import MediaGroupBuilder

from sqlalchemy.ext.asyncio import AsyncSession

from data.text import short_info

from filter.filter import ChatTypeFilter

servises_router = Router()
servises_router.message.filter(ChatTypeFilter(['private']))

def get_services_kb():
    buttons = [
        [InlineKeyboardButton(text="Верификация участника кружков", url="http://uslugi.mosreg.ru")],
        [InlineKeyboardButton(text="Аренда помещений", callback_data="rent_menu")],
        [InlineKeyboardButton(text="Обратная связь",
                              url="https://forms.mkrf.ru/e/2579/xTPLeBU7/?ap_orgcode=640160132")],
        [InlineKeyboardButton(text="🏠 В Главное меню", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@servises_router.message(Command('services'))
async def notification(message: types.Message, session: AsyncSession):
    await message.answer("Список дополнительных услуг", reply_markup=get_services_kb())

@servises_router.callback_query(F.data == 'rent_menu')
async def rent_menu(callback: CallbackQuery):
    msg_id = callback.message.message_id
    rent_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Большой зал", callback_data=f'big_hall_{msg_id}')],
        [InlineKeyboardButton(text="Малый зал", callback_data=f'small_hall_{msg_id}')],
        [InlineKeyboardButton(text="Бальный зал", callback_data=f'dance_hall_{msg_id}')],
        [InlineKeyboardButton(text="Аренда Помещений (прайс)",
                              url="https://дк-яуза.рф/upload/iblock/d14/6tpgb3m5717z0eaxa0ghbx386zvtgnut.pdf")],
        [InlineKeyboardButton(text="Ссылка на сайт",
                              url="https://дк-яуза.рф/prostranstva/")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data='services')]

    ])
    await callback.message.edit_text('Аренда помещений', reply_markup=rent_menu_kb)


big_hall_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data='rent_menu')]
])

@servises_router.callback_query(F.data.startswith("big_hall"))
async def big_hall_menu(callback: CallbackQuery, bot: Bot):
    msg_id = callback.data.split('_')[-1]
    url_img = ['https://дк-яуза.рф/upload/iblock/e8e/9rghh0bjp38ly4r1y3r2mq5cuvgbinrb.JPG','https://дк-яуза.рф/upload/iblock/823/sp566u4xoqrwnjrgsrdu3qu8kgon4b1u.JPG',
               'https://дк-яуза.рф/upload/iblock/cb9/0o2ej2atw4xysmb7wxy3w23pcn6pkd9l.JPG','https://дк-яуза.рф/upload/iblock/823/sp566u4xoqrwnjrgsrdu3qu8kgon4b1u.JPG',
               'https://дк-яуза.рф/upload/iblock/27f/5rtlo69rtr9oc2xlqi96dv81k6lbbqk3.JPG','https://дк-яуза.рф/upload/iblock/411/6w2d08uszkngv2x5fj0s1m5d4j6qap9x.JPG',
               'https://дк-яуза.рф/upload/iblock/2eb/b75klduuthr2exo96w3jjnamuv5n8xmn.jpg']
    try:
        await bot.delete_message(callback.message.chat.id,int(msg_id))
    except:
        pass
    text = (
        f"<b>Большой Зал\n\n</b>"
        f"Вместимость: \t 848 мест\n"
        f"Концерты/Конференции/Спектакли"
        )
    media_group = MediaGroupBuilder(caption=text)
    for photo_url in url_img:
        media_group.add_photo(type='photo', media=photo_url)
    await callback.message.answer_media_group(media=media_group.build())
    await callback.message.answer(short_info, reply_markup=big_hall_kb)

@servises_router.callback_query(F.data.startswith("small_hall_"))
async def hall_menu_1(callback: CallbackQuery, bot: Bot):
    msg_id = callback.data.split('_')[-1]
    url_img = ['https://дк-яуза.рф/upload/iblock/ba6/xrmzvi87418sfqc38ll2ylfmwgyvg9e7.jpg','https://дк-яуза.рф/upload/iblock/4dc/1sq4mqz0oizplwwbbvopk5x84gid0u1z.jpg',
               'https://дк-яуза.рф/upload/iblock/817/v80u79rcnzzo020ydtyzpfdad4dxqj40.jpg','https://дк-яуза.рф/upload/iblock/15d/v4v6v1188sgy2e0hoptjwhsooap81nz5.jpg',
               'https://дк-яуза.рф/upload/iblock/e68/hi5g190n6w2hrp64t7t7i01oa3o2cwva.jpg','https://дк-яуза.рф/upload/iblock/0aa/jmqkpac422l8422w8ychyitz32heazup.jpg']
    try:
        await bot.delete_message(callback.message.chat.id,int(msg_id))
    except:
        pass
    text = (
        f"<b>Малый Зал\n\n</b>"
        f"Вместимость: \t 204 места\n"
        f"Концерты/Конференции/Спектакли"
        )
    media_group = MediaGroupBuilder(caption=text)
    for photo_url in url_img:
        media_group.add_photo(type='photo', media=photo_url)
    await callback.message.answer_media_group(media=media_group.build())
    await callback.message.answer(short_info, reply_markup=big_hall_kb)

@servises_router.callback_query(F.data.startswith("small_hall_"))
async def hall_menu_2(callback: CallbackQuery, bot: Bot):
    msg_id = callback.data.split('_')[-1]
    url_img = ['https://дк-яуза.рф/upload/iblock/ba6/xrmzvi87418sfqc38ll2ylfmwgyvg9e7.jpg',
               'https://дк-яуза.рф/upload/iblock/4dc/1sq4mqz0oizplwwbbvopk5x84gid0u1z.jpg',
               'https://дк-яуза.рф/upload/iblock/817/v80u79rcnzzo020ydtyzpfdad4dxqj40.jpg',
               'https://дк-яуза.рф/upload/iblock/15d/v4v6v1188sgy2e0hoptjwhsooap81nz5.jpg',
               'https://дк-яуза.рф/upload/iblock/e68/hi5g190n6w2hrp64t7t7i01oa3o2cwva.jpg',
               'https://дк-яуза.рф/upload/iblock/0aa/jmqkpac422l8422w8ychyitz32heazup.jpg']
    try:
        await bot.delete_message(callback.message.chat.id, int(msg_id))
    except:
        pass
    text = (
        f"<b>Малый Зал\n\n</b>"
        f"Вместимость: \t 204 места\n"
        f"Концерты/Конференции/Спектакли"
    )
    media_group = MediaGroupBuilder()
    for photo_url in url_img:
        media_group.add_photo(type='photo', media=photo_url)
    await callback.message.answer_media_group(media=media_group.build())
    await callback.message.answer(text, reply_markup=big_hall_kb)


@servises_router.callback_query(F.data.startswith("dance_hall_"))
async def hall_menu_3(callback: CallbackQuery, bot: Bot):
    msg_id = callback.data.split('_')[-1]
    url_img = ['https://дк-яуза.рф/upload/iblock/3df/72pwgvfgf8vynkz1mqrqc19t2tjdkac0.JPG','https://дк-яуза.рф/upload/iblock/7d1/o6p930nom2fqpn3pzh3d9dndd9ml0qji.JPG',
               'https://дк-яуза.рф/upload/iblock/a80/ntrw4n887g0rh2twaiykc0fip252onvs.JPG','https://дк-яуза.рф/upload/iblock/ae1/yg5rlae0o0fb8tfxrr2t1wkymtwlp6nd.JPG']
    try:
        await bot.delete_message(callback.message.chat.id,int(msg_id))
    except:
        pass
    text = f"<b>Бальный Зал\n\n</b>"
    media_group = MediaGroupBuilder(caption=text)
    for photo_url in url_img:
        media_group.add_photo(type='photo', media=photo_url)
    await callback.message.answer_media_group(media=media_group.build())
    await callback.message.answer(short_info, reply_markup=big_hall_kb)