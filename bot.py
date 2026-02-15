import logging
import html
import time
import datetime
from collections import deque
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)

# --- 1. НАСТРОЙКИ ---
# Оригинальный токен и PUBLICATION MODE (TEST_MODE = False)
TOKEN = "8399814024:AAEla8xBVk_9deHydJV0hrc5QYDyXAFpZ8k"
ADMIN_ID = 1615492914
TEST_MODE = False  # ТЕПЕРЬ ПУБЛИКАЦИЯ ИДЕТ В КАНАЛЫ

# Глобальные переменные
PAID_MODE = False
CURRENT_QR_ID = None # Хранит ID текущего QR кода

CHANNELS_CONFIG = {
    "bishkek": {
        "name": "Бишкек", 
        "channel_id": -1003898037632, 
        "categories": {"flowers": 11, "jewelry": 12, "gifts": 13, "certs": 14}
    },
    "osh": {
        "name": "Ош", 
        "channel_id": -1003840234187, 
        "categories": {"flowers": 4, "jewelry": 6, "gifts": 5, "certs": 30}
    },
    "jalalabad": {
        "name": "Джалал-Абад", 
        "channel_id": -1003764029224, 
        "categories": {"flowers": 4, "jewelry": 6, "gifts": 5, "certs": 7}
    },
    "tokmok": {
        "name": "Токмок", 
        "channel_id": -1003770208724, 
        "categories": {"flowers": 2, "jewelry": 8, "gifts": 3, "certs": 7}
    },
    "karakol": {
        "name": "Каракол", 
        "channel_id": -1003816222380, 
        "categories": {"flowers": 2, "jewelry": 8, "gifts": 3, "certs": 7}
    },
}
EXTRA_FLOWERS_CHANNEL = -1002930228617 

STRINGS = {
    'ru': {
        'welcome': "🇰🇬 <b>КЫРГЫЗСТАН ПОДАРКИ</b>\n━━━━━━━━━━━━━━━\nВыберите действие:",
        'btn_post': "🌹 Выложить объявление",
        'btn_support': "💬 Поддержка",
        'btn_back': "🔙 Назад",
        'btn_cancel': "❌ Отмена",
        'btn_done': "✅ ФОТО ЗАГРУЖЕНЫ",
        'btn_finish_chat': "🏁 ЗАВЕРШИТЬ ЧАТ",
        'step_1': "<b>📸 ШАГ 1: ФОТО</b>\nОтправьте до 10 фото, затем нажмите 👇",
        'step_2': "<b>📍 ШАГ 2: ГОРОД</b>",
        'step_3': "<b>🏠 ШАГ 3: АДРЕС</b>\nВведите адрес магазина или района:",
        'step_4': "<b>📁 ШАГ 4: КАТЕГОРИЯ</b>",
        'step_5': "<b>📝 ШАГ 5: НАЗВАНИЕ</b>\nЧто именно вы продаете?",
        'step_6': "<b>🕒 ШАГ 6: ВРЕМЯ</b>\nУкажите время работы или доставки:",
        'step_7': "<b>💰 ШАГ 7: ЦЕНА</b>\nВведите цену в сомах:",
        'step_8': "<b>📱 ШАГ 8: WHATSAPP</b>\nВведите номер телефона:",
        'step_pay': "<b>💳 ОПЛАТА</b>\nИз-за праздников публикация платная — <b>100 сом</b>.\n\nПожалуйста, оплатите по QR-коду выше 👆 и <b>отправьте скриншот чека</b> сюда.",
        'wait': "✅ <b>Принято!</b> Ваша заявка и чек отправлены на проверку. Как только модератор освободится, он примет её или ответит вам.",
        'rejected': "❌ <b>Заявка отклонена.</b>",
        'reason_prefix': "📝 <b>Причина:</b> ",
        'support_open': "🤝 <b>ЧАТ ОТКРЫТ</b>\nПишите сообщение. Модератор ответит здесь.",
        'chat_finished': "🏁 Чат завершен.",
        'edit_menu': "⚙️ <b>ЧТО ИЗМЕНИТЬ?</b>",
        'field_flowers': "📝 Название",
        'field_price': "💰 Цена",
        'field_address': "📍 Адрес",
        'field_whatsapp': "📞 WhatsApp",
        'sold_warn': "⚠️ <b>ВЫ УВЕРЕНЫ?</b>\n\nПосле отметки «Продано» пост будет изменен, и вы больше не сможете его редактировать или продвигать.",
        'btn_confirm_sold': "✅ Да, продано",
        'cats': {"flowers": "Цветы 🌸", "jewelry": "Ювелирка 💎", "gifts": "Подарки 🎁", "certs": "Сертификаты 🎟"}
    },
    'kg': {
        'welcome': "🇰🇬 <b>КЫРГЫЗСТАН БЕЛЕКТЕР</b>\n━━━━━━━━━━━━━━━\nАракетти тандаңыз:",
        'btn_post': "🌹 Жарыя кошуу",
        'btn_support': "💬 Жардам",
        'btn_back': "🔙 Артка",
        'btn_cancel': "❌ Токтотуу",
        'btn_done': "✅ СҮРӨТТӨР ЖҮКТӨЛДҮ",
        'btn_finish_chat': "🏁 ЧАТТЫ БҮТҮРҮҮ",
        'step_1': "<b>📸 1-КАДАМ: СҮРӨТ</b>\nСүрөт жөнөтүп, 👇 басыңыз",
        'step_2': "<b>📍 2-КАДАМ: ШААР</b>",
        'step_3': "<b>🏠 3-КАДАМ: ДАРЕК</b>\nДаректи жазыңыз:",
        'step_4': "<b>📁 4-КАДАМ: КАТЕГОРИЯ</b>",
        'step_5': "<b>📝 5-КАДАМ: АТАЛЫШЫ</b>\nЭмне сатасыз?",
        'step_6': "<b>🕒 6-КАДАМ: УБАКЫТ</b>\nУбакытты жазыңыз:",
        'step_7': "<b>💰 7-КАДАМ: БААСЫ</b>\nБаасын жазыңыз:",
        'step_8': "<b>📱 8-КАДАМ: WHATSAPP</b>\nТелефон номериңиз:",
        'step_pay': "<b>💳 ТӨЛӨӨ</b>\nМайрамдарга байланыштуу жарыя чыгаруу акылуу — <b>100 сом</b>.\n\nQR-код менен төлөп 👆, <b>чектин сүрөтүн (скриншот)</b> жөнөтүңүз.",
        'wait': "✅ <b>Кабыл алынды!</b> Сиздин билдирүүңүз и чегиңиз текшерүүгө жөнөтүлдү. Модератор бошогондо аны кабыл алат же сизге жооп берет.",
        'rejected': "❌ <b>Жарыя четке кагылды.</b>",
        'reason_prefix': "📝 <b>Себеби:</b> ",
        'support_open': "🤝 <b>ЧАТ АЧЫЛДЫ</b>\nЖазыңыз, модератор жооп берет.",
        'chat_finished': "🏁 Чат аяктады.",
        'edit_menu': "⚙️ <b>ЭМНЕНИ ӨЗГӨРТҮҮ КЕРЕК?</b>",
        'field_flowers': "📝 Аталышы",
        'field_price': "💰 Баасы",
        'field_address': "📍 Дарек",
        'field_whatsapp': "📞 WhatsApp",
        'sold_warn': "⚠️ <b>ИШЕНЕСИЗБИ?</b>\n\n«Сатылды» деп белгиленгенден кийин билдирүү өзгөрөт и сиз аны кайра өзгертө албайсыз.",
        'btn_confirm_sold': "✅ Ооба, сатылды",
        'cats': {"flowers": "Гүлдөр 🌸", "jewelry": "Зергер буюмдар 💎", "gifts": "Белектер 🎁", "certs": "Сертификаттар 🎟"}
    }
}

db_ads = {}
db_users = {} 
db_user_dates = {} # Хранит время регистрации юзера

active_support_chat = None 
support_queue = deque()

# Состояния: PAYMENT - ожидание скрина оплаты, GET_QR - ожидание QR от админа
PHOTO, CITY, ADDRESS, CATEGORY, FLOWERS, DATE, PRICE, WHATSAPP, PAYMENT = range(9)
GET_QR = 10 

logging.basicConfig(level=logging.INFO)

# --- УТИЛИТЫ ---

def format_caption(data, is_sold=False):
    f = html.escape(str(data.get('flowers', '—')))
    p = html.escape(str(data.get('price', '—')))
    d = html.escape(str(data.get('date', '—')))
    a = html.escape(str(data.get('address', '—')))
    w = html.escape(str(data.get('whatsapp', '—')))
    if is_sold:
        return f"<b>✅ ПРОДАНО / САТЫЛДЫ</b>\n━━━━━━━━━━━━━━━\n📦 <b>ТОВАР:</b> {f}\n💰 <b>ЦЕНА:</b> {p}"
    return f"🏷 <b>ТОВАР:</b> {f}\n━━━━━━━━━━━━━━━\n💰 <b>ЦЕНА:</b> {p}\n🕒 <b>ВРЕМЯ:</b> {d}\n📍 <b>АДРЕС:</b> {a}\n📞 <b>СВЯЗЬ:</b> {w}\n━━━━━━━━━━━━━━━\n🤖 @kyrgyzstanpodarkibot"

async def clear_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'last_msg' in context.user_data:
        try:
            await context.bot.delete_message(update.effective_chat.id, context.user_data['last_msg'])
        except: pass
    
    # Также удаляем сообщение с оплатой (QR-кодом), если оно было
    if 'pay_msg_id' in context.user_data:
        try:
            await context.bot.delete_message(update.effective_chat.id, context.user_data['pay_msg_id'])
            del context.user_data['pay_msg_id']
        except: pass

async def finalize_ad(update, context, u_id, payment_screen_id=None):
    lang = db_users.get(u_id, 'ru')
    # ID заявки - это текущее время в секундах
    ad_id = str(int(time.time()))
    
    db_ads[ad_id] = {
        'user_id': u_id, 'city_key': context.user_data['city_key'], 'cat_key': context.user_data['cat_key'],
        'flowers': context.user_data['flowers'], 'price': context.user_data['price'], 'date': context.user_data['date'],
        'address': context.user_data['address'], 'whatsapp': context.user_data['whatsapp'], 'photos': context.user_data['photos'],
        'payment_screen': payment_screen_id
    }
    
    await clear_ui(update, context)
    
    ad = db_ads[ad_id]
    adm_cap = f"📑 <b>ЗАЯВКА</b>\n👤 @{update.effective_user.username}\n📍 {CHANNELS_CONFIG[ad['city_key']]['name']} | {STRINGS['ru']['cats'][ad['cat_key']]}\n\n{format_caption(ad)}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("ОДОБРИТЬ ✅", callback_data=f"apub_{ad_id}"), InlineKeyboardButton("ОТКЛОНИТЬ ❌", callback_data=f"arej_{ad_id}")],
        [InlineKeyboardButton("⚙️ КАТЕГОРИЯ", callback_data=f"achg_{ad_id}")]
    ])
    
    if payment_screen_id:
        await context.bot.send_photo(ADMIN_ID, payment_screen_id, caption=f"💰 <b>ОПЛАТА ПО ЗАЯВКЕ</b>\nID: {ad_id}\nПроверьте чек 👇", parse_mode='HTML')
        
    await context.bot.send_photo(ADMIN_ID, ad['photos'][0], caption=adm_cap, reply_markup=kb, parse_mode='HTML')
    await context.bot.send_message(u_id, STRINGS[lang]['wait'], parse_mode='HTML')

# --- АДМИН: НАСТРОЙКА ОПЛАТЫ ---

async def cmd_nomoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    global PAID_MODE, CURRENT_QR_ID
    PAID_MODE = False
    CURRENT_QR_ID = None
    await update.message.reply_text("✅ <b>Бесплатный режим включен.</b>", parse_mode='HTML')

async def cmd_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("📸 <b>Отправьте фото QR-кода.</b>", parse_mode='HTML')
    return GET_QR

async def admin_get_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo: return GET_QR
    global PAID_MODE, CURRENT_QR_ID
    CURRENT_QR_ID = update.message.photo[-1].file_id
    PAID_MODE = True
    await update.message.reply_text("✅ <b>Платный режим ВКЛЮЧЕН!</b>", parse_mode='HTML')
    return ConversationHandler.END

# --- ГЛАВНЫЕ КОМАНДЫ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id = update.effective_user.id
    context.user_data.clear()
    
    # Записываем время регистрации для статистики
    if u_id not in db_user_dates:
        db_user_dates[u_id] = time.time()
    
    if update.callback_query: await update.callback_query.answer()

    if u_id not in db_users:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Русский 🇷🇺", callback_data="sl_ru"), 
                                    InlineKeyboardButton("Кыргызча 🇰🇬", callback_data="sl_kg")]])
        if update.message:
            await update.message.reply_text("Выберите язык / Тилди тандаңыз:", reply_markup=kb)
        else:
            await update.callback_query.message.edit_text("Выберите язык / Тилди тандаңыз:", reply_markup=kb)
        return ConversationHandler.END

    lang = db_users[u_id]
    s = STRINGS[lang]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(s['btn_post'], callback_data="main_post")], 
                               [InlineKeyboardButton(s['btn_support'], callback_data="main_support")]])
    if update.callback_query:
        if update.callback_query.data == "cancel_pay":
            try: await update.callback_query.message.delete()
            except: pass
            msg = await context.bot.send_message(u_id, s['welcome'], reply_markup=kb, parse_mode='HTML')
            context.user_data['last_msg'] = msg.message_id
        else:
            await update.callback_query.message.edit_text(s['welcome'], reply_markup=kb, parse_mode='HTML')
    else:
        msg = await update.message.reply_text(s['welcome'], reply_markup=kb, parse_mode='HTML')
        context.user_data['last_msg'] = msg.message_id
    return ConversationHandler.END

async def admin_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    # Определяем начало "сегодня" и "вчера"
    now = datetime.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    yesterday_start = today_start - 86400

    # Считаем заявки
    ads_today = 0
    ads_yesterday = 0
    for ad_id in db_ads:
        try:
            t = float(ad_id) # ad_id это timestamp
            if t >= today_start:
                ads_today += 1
            elif t >= yesterday_start:
                ads_yesterday += 1
        except: pass

    # Считаем юзеров
    users_today = 0
    users_yesterday = 0
    for reg_time in db_user_dates.values():
        if reg_time >= today_start:
            users_today += 1
        elif reg_time >= yesterday_start:
            users_yesterday += 1

    mode = "ПЛАТНЫЙ 💰" if PAID_MODE else "БЕСПЛАТНЫЙ 🆓"
    
    text = (
        f"📊 <b>СТАТИСТИКА</b>\n\n"
        f"📅 <b>СЕГОДНЯ:</b>\n"
        f"👤 Новых юзеров: {users_today}\n"
        f"📝 Заявок: {ads_today}\n\n"
        
        f"🗓 <b>ВЧЕРА:</b>\n"
        f"👤 Новых юзеров: {users_yesterday}\n"
        f"📝 Заявок: {ads_yesterday}\n\n"
        
        f"📈 <b>ВСЕГО:</b>\n"
        f"👤 Юзеров: {len(db_users)}\n"
        f"📝 Заявок: {len(db_ads)}\n\n"
        
        f"⚙️ <b>Статус:</b>\n"
        f"Очередь поддержки: {len(support_queue)}\n"
        f"Режим: {mode}"
    )
    
    await update.message.reply_text(text, parse_mode='HTML')

async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    u_id = query.from_user.id
    db_users[u_id] = query.data.split("_")[1]
    if u_id not in db_user_dates:
        db_user_dates[u_id] = time.time()
    await query.answer()
    return await start(update, context)

# --- АНКЕТА ---

async def post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    lang = db_users.get(update.effective_user.id, 'ru')
    context.user_data['photos'] = []
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(STRINGS[lang]['btn_done'], callback_data="photos_done")],
                               [InlineKeyboardButton(STRINGS[lang]['btn_cancel'], callback_data="to_main")]])
    if query:
        await query.message.edit_text(STRINGS[lang]['step_1'], reply_markup=kb, parse_mode='HTML')
        context.user_data['last_msg'] = query.message.message_id
    return PHOTO

async def post_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['photos'].append(update.message.photo[-1].file_id)
    return PHOTO

async def post_photos_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = db_users.get(update.effective_user.id, 'ru')
    if not context.user_data.get('photos'):
        await update.callback_query.answer("Загрузите фото!", show_alert=True)
        return PHOTO
    await clear_ui(update, context)
    kb = [[InlineKeyboardButton(v['name'], callback_data=f"city_{k}")] for k, v in CHANNELS_CONFIG.items()]
    kb.append([InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data="back_to_photo_start")])
    msg = await context.bot.send_message(update.effective_chat.id, STRINGS[lang]['step_2'], reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    context.user_data['last_msg'] = msg.message_id
    return CITY

async def post_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = db_users.get(query.from_user.id, 'ru')
    if query.data.startswith("city_"): context.user_data['city_key'] = query.data.replace("city_", "")
    await query.answer()
    await clear_ui(update, context)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data="photos_done")]])
    msg = await query.message.reply_text(STRINGS[lang]['step_3'], reply_markup=kb, parse_mode='HTML')
    context.user_data['last_msg'] = msg.message_id
    return ADDRESS

async def post_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        context.user_data['address'] = update.message.text
        await clear_ui(update, context)
    lang = db_users.get(update.effective_user.id, 'ru')
    kb = [[InlineKeyboardButton(v, callback_data=f"cat_{k}")] for k, v in STRINGS[lang]['cats'].items()]
    kb.append([InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data="back_to_city")])
    msg = await context.bot.send_message(update.effective_chat.id, STRINGS[lang]['step_4'], reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    context.user_data['last_msg'] = msg.message_id
    return CATEGORY

async def post_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = db_users.get(query.from_user.id, 'ru')
    if query.data.startswith("cat_"): context.user_data['cat_key'] = query.data.replace("cat_", "")
    await query.answer()
    await clear_ui(update, context)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data="back_to_addr")]])
    msg = await query.message.reply_text(STRINGS[lang]['step_5'], reply_markup=kb, parse_mode='HTML')
    context.user_data['last_msg'] = msg.message_id
    return FLOWERS

async def post_flowers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        context.user_data['flowers'] = update.message.text
        await clear_ui(update, context)
    lang = db_users.get(update.effective_user.id, 'ru')
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data="back_to_cat")]])
    msg = await context.bot.send_message(update.effective_chat.id, STRINGS[lang]['step_6'], reply_markup=kb, parse_mode='HTML')
    context.user_data['last_msg'] = msg.message_id
    return DATE

async def post_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        context.user_data['date'] = update.message.text
        await clear_ui(update, context)
    lang = db_users.get(update.effective_user.id, 'ru')
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data="back_to_flowers")]])
    msg = await context.bot.send_message(update.effective_chat.id, STRINGS[lang]['step_7'], reply_markup=kb, parse_mode='HTML')
    context.user_data['last_msg'] = msg.message_id
    return PRICE

async def post_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        context.user_data['price'] = update.message.text
        await clear_ui(update, context)
    lang = db_users.get(update.effective_user.id, 'ru')
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data="back_to_date")]])
    msg = await context.bot.send_message(update.effective_chat.id, STRINGS[lang]['step_8'], reply_markup=kb, parse_mode='HTML')
    context.user_data['last_msg'] = msg.message_id
    return WHATSAPP

async def post_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['whatsapp'] = update.message.text
    u_id = update.effective_user.id
    lang = db_users.get(u_id, 'ru')
    await clear_ui(update, context)

    if PAID_MODE and CURRENT_QR_ID:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(STRINGS[lang]['btn_cancel'], callback_data="cancel_pay")]])
        msg = await context.bot.send_photo(u_id, CURRENT_QR_ID, caption=STRINGS[lang]['step_pay'], parse_mode='HTML', reply_markup=kb)
        # Запоминаем ID сообщения с оплатой, чтобы убрать кнопку потом
        context.user_data['pay_msg_id'] = msg.message_id
        return PAYMENT
    else:
        await finalize_ad(update, context, u_id)
        return ConversationHandler.END

async def post_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        lang = db_users.get(update.effective_user.id, 'ru')
        await update.message.reply_text("Пожалуйста, отправьте фото (скриншот)!" if lang=='ru' else "Сураныч, сүрөт жөнөтүңүз!")
        return PAYMENT
    
    # Убираем кнопку отмены с сообщения QR кода
    if 'pay_msg_id' in context.user_data:
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=update.effective_chat.id, 
                message_id=context.user_data['pay_msg_id'], 
                reply_markup=None
            )
        except: pass

    screen_id = update.message.photo[-1].file_id
    await finalize_ad(update, context, update.effective_user.id, payment_screen_id=screen_id)
    return ConversationHandler.END

# --- АДМИН ПУБЛИКАЦИЯ ---

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    action, ad_id = data[0], data[1]
    ad = db_ads.get(ad_id)
    if not ad: return

    if action == "apub":
        await query.answer()
        target = ADMIN_ID if TEST_MODE else CHANNELS_CONFIG[ad['city_key']]['channel_id']
        thread = CHANNELS_CONFIG[ad['city_key']]['categories'][ad['cat_key']] if not TEST_MODE else None
        cap = format_caption(ad)
        
        try:
            if len(ad['photos']) == 1:
                msg = await context.bot.send_photo(target, ad['photos'][0], caption=cap, parse_mode='HTML', message_thread_id=thread)
            else:
                media = [InputMediaPhoto(ad['photos'][0], caption=cap, parse_mode='HTML')]
                for ph in ad['photos'][1:10]: media.append(InputMediaPhoto(ph))
                msgs = await context.bot.send_media_group(target, media, message_thread_id=thread)
                msg = msgs[0]
            db_ads[ad_id].update({'m_id': msg.message_id, 'c_id': target})

            if ad['city_key'] == "bishkek" and ad['cat_key'] == "flowers":
                ex_target = ADMIN_ID if TEST_MODE else EXTRA_FLOWERS_CHANNEL
                try:
                    if len(ad['photos']) == 1:
                        ex_msg = await context.bot.send_photo(ex_target, ad['photos'][0], caption=cap, parse_mode='HTML')
                    else:
                        media_ex = [InputMediaPhoto(ad['photos'][0], caption=cap, parse_mode='HTML')]
                        for ph in ad['photos'][1:10]: media_ex.append(InputMediaPhoto(ph))
                        ex_msgs = await context.bot.send_media_group(ex_target, media_ex)
                        ex_msg = ex_msgs[0]
                    db_ads[ad_id]['ex_m_id'], db_ads[ad_id]['ex_c_id'] = ex_msg.message_id, ex_target
                except: pass

            kb = InlineKeyboardMarkup([[InlineKeyboardButton("📝 Изменить", callback_data=f"uedit_{ad_id}"), InlineKeyboardButton("✅ Продано", callback_data=f"usold_{ad_id}")]])
            await context.bot.send_message(ad['user_id'], "🎉 Ваше объявление опубликовано!", reply_markup=kb)
            await query.message.delete()
        except Exception as e:
            await query.message.reply_text(f"Ошибка публикации: {e}")

    elif action == "arej":
        await query.answer()
        u_id = ad['user_id']
        lang = db_users.get(u_id, 'ru')
        await context.bot.send_message(u_id, STRINGS[lang]['rejected'], parse_mode='HTML')
        context.bot_data['wait_rej'] = u_id
        await query.message.delete()
        await context.bot.send_message(ADMIN_ID, f"❌ Отклонено {ad_id}. Напишите причину:")

    elif action == "achg":
        await query.answer()
        kb = [[InlineKeyboardButton(v, callback_data=f"asetcat_{ad_id}_{k}")] for k, v in STRINGS['ru']['cats'].items()]
        await query.message.edit_caption(caption="Выберите категорию:", reply_markup=InlineKeyboardMarkup(kb))

async def admin_set_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, ad_id, new_cat = query.data.split("_")
    if ad_id in db_ads:
        db_ads[ad_id]['cat_key'] = new_cat
        ad = db_ads[ad_id]
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("ОДОБРИТЬ ✅", callback_data=f"apub_{ad_id}"), InlineKeyboardButton("ОТКЛОНИТЬ ❌", callback_data=f"arej_{ad_id}")], [InlineKeyboardButton("⚙️ КАТЕГОРИЯ", callback_data=f"achg_{ad_id}")]])
        await query.message.edit_caption(caption=f"Категория изменена!\n\n{format_caption(ad)}", reply_markup=kb, parse_mode='HTML')

# --- ПОДДЕРЖКА ---

async def support_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_support_chat
    u_id = update.effective_user.id
    lang = db_users.get(u_id, 'ru')
    if update.callback_query: await update.callback_query.answer()
    
    if active_support_chat == u_id: return
    if active_support_chat is None:
        active_support_chat = u_id
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(STRINGS[lang]['btn_finish_chat'], callback_data="finish_chat")]])
        await context.bot.send_message(u_id, STRINGS[lang]['support_open'], reply_markup=kb, parse_mode='HTML')
        
        q_len = len(support_queue)
        q_text = f"\n👥 В очереди: {q_len}" if q_len > 0 else ""
        await context.bot.send_message(ADMIN_ID, f"🆘 ЧАТ: @{update.effective_user.username}{q_text}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏁 ЗАВЕРШИТЬ", callback_data="finish_chat")]]))
    else:
        if u_id not in support_queue: 
            support_queue.append(u_id)
            await context.bot.send_message(ADMIN_ID, f"🆕 Новый человек в очереди! Всего ждут: {len(support_queue)}")
        await context.bot.send_message(u_id, f"Вы в очереди: {list(support_queue).index(u_id)+1}")

async def finish_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_support_chat
    if update.callback_query: await update.callback_query.answer()
    if active_support_chat:
        try:
            l = db_users.get(active_support_chat, 'ru')
            await context.bot.send_message(active_support_chat, STRINGS[l]['chat_finished'])
            await context.bot.send_message(ADMIN_ID, "🏁 Чат закрыт.")
        except: pass
    active_support_chat = None
    if support_queue:
        active_support_chat = support_queue.popleft()
        l = db_users.get(active_support_chat, 'ru')
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(STRINGS[l]['btn_finish_chat'], callback_data="finish_chat")]])
        await context.bot.send_message(active_support_chat, STRINGS[l]['support_open'], reply_markup=kb, parse_mode='HTML')
        await context.bot.send_message(ADMIN_ID, f"🆘 Следующий чат! (Осталось в очереди: {len(support_queue)})", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏁 ЗАВЕРШИТЬ", callback_data="finish_chat")]]))
    else:
        if update.effective_user.id == ADMIN_ID:
            try: await update.callback_query.message.edit_text("🏁 Все чаты закрыты.")
            except: pass

# --- ИЗМЕНЕНИЕ И УПРАВЛЕНИЕ ---

async def user_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    action, ad_id = data[0], data[1]
    ad = db_ads.get(ad_id)
    if not ad: return
    lang = db_users.get(update.effective_user.id, 'ru')
    s = STRINGS[lang]

    if action == "usold":
        # Шаг 1: Подтверждение
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(s['btn_confirm_sold'], callback_data=f"uconf_{ad_id}")],
            [InlineKeyboardButton(s['btn_back'], callback_data=f"uback_{ad_id}")]
        ])
        await query.edit_message_text(s['sold_warn'], reply_markup=kb, parse_mode='HTML')

    elif action == "uconf":
        # Шаг 2: Само действие «Продано»
        for m_key, c_key in [('m_id', 'c_id'), ('ex_m_id', 'ex_c_id')]:
            if m_key in ad:
                try: await context.bot.edit_message_caption(chat_id=ad[c_key], message_id=ad[m_key], caption=format_caption(ad, True), parse_mode='HTML')
                except: pass
        await query.edit_message_text("✅ ТОВАР ПРОДАН / ТОВАР САТЫЛДЫ")

    elif action == "uedit":
        kb = [[InlineKeyboardButton(s['field_flowers'], callback_data=f"uf_flowers_{ad_id}"), InlineKeyboardButton(s['field_price'], callback_data=f"uf_price_{ad_id}")],
              [InlineKeyboardButton(s['field_address'], callback_data=f"uf_address_{ad_id}"), InlineKeyboardButton(s['field_whatsapp'], callback_data=f"uf_whatsapp_{ad_id}")],
              [InlineKeyboardButton(s['btn_back'], callback_data=f"uback_{ad_id}")]]
        await query.edit_message_text(s['edit_menu'], reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

    elif action == "uback":
        kb = [[InlineKeyboardButton("📝 Изменить", callback_data=f"uedit_{ad_id}"), InlineKeyboardButton("✅ Продано", callback_data=f"usold_{ad_id}")]]
        await query.edit_message_text("Меню управления / Башкаруу менюсу:", reply_markup=InlineKeyboardMarkup(kb))

# --- РЕЛЕЙ ---

async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id, text = update.effective_user.id, update.message.text
    if 'edit_field' in context.user_data:
        field, ad_id = context.user_data['edit_field'], context.user_data['edit_ad_id']
        if ad_id in db_ads:
            db_ads[ad_id][field] = text
            ad = db_ads[ad_id]
            for m_key, c_key in [('m_id', 'c_id'), ('ex_m_id', 'ex_c_id')]:
                if m_key in ad:
                    try: await context.bot.edit_message_caption(chat_id=ad[c_key], message_id=ad[m_key], caption=format_caption(ad), parse_mode='HTML')
                    except: pass
            del context.user_data['edit_field']
            kb = [[InlineKeyboardButton("📝 Изменить еще", callback_data=f"uedit_{ad_id}"), InlineKeyboardButton("✅ Продано", callback_data=f"usold_{ad_id}")]]
            await update.message.reply_text("✅ Обновлено!", reply_markup=InlineKeyboardMarkup(kb))
        return
    if u_id == ADMIN_ID and context.bot_data.get('wait_rej'):
        target = context.bot_data['wait_rej']
        lang = db_users.get(target, 'ru')
        await context.bot.send_message(target, f"{STRINGS[lang]['reason_prefix']}{text}", parse_mode='HTML')
        context.bot_data['wait_rej'] = None
        await update.message.reply_text("Причина отправлена.")
        return
    if u_id == ADMIN_ID and active_support_chat: 
        await context.bot.send_message(active_support_chat, f"👨‍💻 {text}")
    elif u_id == active_support_chat:
        q_len = len(support_queue)
        info = f" [Очередь: {q_len}]" if q_len > 0 else ""
        await context.bot.send_message(ADMIN_ID, f"👤 {text}{info}")

async def field_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; _, field, ad_id = query.data.split("_")
    context.user_data['edit_field'], context.user_data['edit_ad_id'] = field, ad_id
    await query.answer(); await query.edit_message_text("✍️ Введите новое значение:")

# --- ЗАПУСК ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('infa', admin_info))
    app.add_handler(CommandHandler('nomoney', cmd_nomoney))
    
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler('money', cmd_money)],
        states={GET_QR: [MessageHandler(filters.PHOTO, admin_get_qr)]},
        fallbacks=[]
    ))
    
    app.add_handler(CallbackQueryHandler(set_lang, pattern="^sl_"))
    app.add_handler(CallbackQueryHandler(admin_decision, pattern="^apub_|^arej_|^achg_"))
    app.add_handler(CallbackQueryHandler(admin_set_category, pattern="^asetcat_"))
    app.add_handler(CallbackQueryHandler(user_actions, pattern="^usold_|^uedit_|^uback_|^uconf_"))
    app.add_handler(CallbackQueryHandler(field_select, pattern="^uf_"))
    app.add_handler(CallbackQueryHandler(start, pattern="^to_main$"))
    app.add_handler(CallbackQueryHandler(support_call, pattern="^main_support$"))
    app.add_handler(CallbackQueryHandler(finish_chat, pattern="^finish_chat$"))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(post_start, pattern="^main_post$")],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, post_photo), CallbackQueryHandler(post_photos_done, pattern="^photos_done$")],
            CITY: [CallbackQueryHandler(post_city, pattern="^city_"), CallbackQueryHandler(post_start, pattern="^back_to_photo_start$")],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_address), CallbackQueryHandler(post_photos_done, pattern="^back_to_photos$")],
            CATEGORY: [CallbackQueryHandler(post_category, pattern="^cat_"), CallbackQueryHandler(post_city, pattern="^back_to_city$")],
            FLOWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_flowers), CallbackQueryHandler(post_category, pattern="^back_to_cat$")],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_date), CallbackQueryHandler(post_flowers, pattern="^back_to_flowers$")],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_price), CallbackQueryHandler(post_date, pattern="^back_to_date$")],
            WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_whatsapp), CallbackQueryHandler(post_price, pattern="^back_to_price$")],
            PAYMENT: [
                MessageHandler(filters.PHOTO, post_payment),
                CallbackQueryHandler(start, pattern="^cancel_pay$")
            ]
        }, fallbacks=[CommandHandler('start', start)]
    ))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay))
    
    app.run_polling()