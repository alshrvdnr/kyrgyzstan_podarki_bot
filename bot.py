import logging
import html
import os
from collections import deque
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# --- 1. НАСТРОЙКИ ---
TOKEN = os.getenv('BOT_TOKEN') 
ADMIN_ID = 1615492914

CHANNELS_CONFIG = {
    "bishkek": {
        "name": "Бишкек Подарки", "channel_id": -1003898037632,
        "categories": {
            "flowers": ("🌸 Цветы", 11), "jewelry": ("💎 Ювелирка", 12),
            "gifts": ("🎁 Подарки", 13), "certs": ("🎟 Сертификаты", 14)
        }
    },
    "osh": {
        "name": "Ош Подарки", "channel_id": -1003840234187,
        "categories": {
            "flowers": ("🌸 Цветы", 4), "jewelry": ("💎 Ювелирка", 6),
            "gifts": ("🎁 Подарки", 5), "certs": ("🎟 Сертификаты", 30)
        }
    },
    "jalalabad": {
        "name": "Джалал-Абад Подарки", "channel_id": -1003764029224,
        "categories": {
            "flowers": ("🌸 Цветы", 4), "gifts": ("🎁 Подарки", 5),
            "jewelry": ("💎 Ювелирка", 6), "certs": ("🎟 Сертификаты", 7)
        }
    }
}

# Состояния анкеты
CITY, ADDRESS, PHOTO, CATEGORY, FLOWERS, DATE, PRICE, WHATSAPP = range(8)
# Состояния редактирования
EDIT_CHOOSE_FIELD, EDIT_INPUT_VALUE = range(8, 10)

logging.basicConfig(level=logging.INFO)

db = {} 
active_support_chat = None 
support_queue = deque()    

# Команды только для главного меню и саппорта
FOOTER_CMD = "\n\n━━━━━━━━━━━━━━━\n🌹 /post | 💬 /support "

# --- УТИЛИТЫ ДИЗАЙНА ---

def format_caption(data, is_sold=False):
    f = html.escape(str(data.get('flowers', '—')))
    p = html.escape(str(data.get('price', '—')))
    d = html.escape(str(data.get('date', '—')))
    a = html.escape(str(data.get('address', '—')))
    w = html.escape(str(data.get('whatsapp', '—')))

    if is_sold:
        return (
            f"<b>✅ СТАТУС: ПРОДАНО / НЕАКТУАЛЬНО</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📦 <b>ТОВАР:</b> {f}\n"
            f"💰 <b>БЫЛА ЦЕНА:</b> {p}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<i>Объявление закрыто владельцем через @kyrgyzstanpodarkibot</i>"
        )
    
    return (
        f"🏷 <b>ТОВАР:</b> {f}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 <b>ЦЕНА:</b> {p}\n"
        f"🕒 <b>ВРЕМЯ:</b> {d}\n"
        f"📍 <b>АДРЕС:</b> {a}\n"
        f"📞 <b>СВЯЗЬ:</b> {w}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🤖 <b>Разместить объявление:</b> @kyrgyzstanpodarkibot"
    )

def get_control_keyboard(u_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 ИЗМЕНИТЬ ДАННЫЕ", callback_data=f"usr_edit_{u_id}")],
        [InlineKeyboardButton("✅ ТОВАР ПРОДАН", callback_data=f"usr_sold_{u_id}")]
    ])

# --- ОБРАБОТЧИКИ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🇰🇬 <b>ВАС ПРИВЕТСТВУЕТ СЕРВИС «КЫРГЫЗСТАН ПОДАРКИ»!</b>\n\n"
        "Мы создали единую площадку для перепродажи букетов, ювелирных изделий и подарочных сертификатов.\n\n"
        "✨ <b>Наши возможности:</b>\n"
        "• Публикация в крупнейших региональных каналах страны.\n"
        "• Удобное управление вашим объявлением.\n"
        "• Живой чат с модератором для помощи.\n\n"
        "🚀 <b>МЕНЮ:</b>\n"
        "🌹 /post — Разместить объявление\n"
        "💬 /support — Написать в поддержку\n\n"
        "<i>Нажмите /post, чтобы начать создание вашей карточки товара!</i>"
    )
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=ReplyKeyboardRemove())

# --- СОЗДАНИЕ ПОСТА (/post) ---

async def post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton(v['name'], callback_data=f"city_{k}")] for k, v in CHANNELS_CONFIG.items()]
    text = (
        "<b>📍 ШАГ 1 из 8: ВЫБОР РЕГИОНА</b>\n\n"
        "Пожалуйста, выберите город. Ваше объявление будет опубликовано именно в канале выбранного города."
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    return CITY

async def post_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['city_key'] = query.data.replace("city_", "")
    text = (
        "<b>🏠 ШАГ 2 из 8: ВАШ АДРЕС</b>\n\n"
        "Пожалуйста, напишите адрес или ориентир (район, ТЦ, пересечение улиц), где находится товар.\n\n"
        "<i>Пример: 7-й микрорайон, ТЦ Ала-Арча или Ахунбаева/Байтик-Баатыра.</i>"
    )
    await query.edit_message_text(text, parse_mode='HTML')
    return ADDRESS

async def post_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    text = (
        "<b>📸 ШАГ 3 из 8: ФОТОГРАФИЯ ТОВАРА</b>\n\n"
        "Пожалуйста, отправьте <b>одну качественную фотографию</b> вашего товара.\n\n"
        "💡 <i>Совет: Четкое фото при хорошем освещении значительно повышает шансы на быструю продажу!</i>"
    )
    await update.message.reply_text(text, parse_mode='HTML')
    return PHOTO

async def post_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("⚠️ <b>ОШИБКА:</b> Пожалуйста, отправьте фото как изображение (не документ).")
        return PHOTO
    context.user_data['photo'] = update.message.photo[-1].file_id
    city = context.user_data['city_key']
    kb = [[InlineKeyboardButton(n, callback_data=f"cat_{k}")] for k, (n, tid) in CHANNELS_CONFIG[city]['categories'].items()]
    text = (
        "<b>📁 ШАГ 4 из 8: КАТЕГОРИЯ</b>\n\n"
        "Выберите категорию вашего товара. Это необходимо для сортировки во вкладках канала."
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    return CATEGORY

async def post_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['cat_key'] = query.data.replace("cat_", "")
    text = (
        "<b>📝 ШАГ 5 из 8: НАЗВАНИЕ</b>\n\n"
        "Кратко опишите ваш товар.\n\n"
        "📖 <b>Пример:</b> <i>Букет из 25 роз «Ред Наоми»</i> или <i>Золотые серьги 585 пробы.</i>"
    )
    await query.edit_message_text(text, parse_mode='HTML')
    return FLOWERS

async def post_flowers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['flowers'] = update.message.text
    text = (
        "<b>🕒 ШАГ 6 из 8: ВРЕМЯ И СВЕЖЕСТЬ</b>\n\n"
        "Укажите, когда был куплен или получен товар. Это важно для покупателей.\n\n"
        "📖 <b>Пример:</b> <i>Сегодня утром</i> или <i>Вчера в 19:00.</i>"
    )
    await update.message.reply_text(text, parse_mode='HTML')
    return DATE

async def post_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date'] = update.message.text
    text = (
        "<b>💰 ШАГ 7 из 8: СТОИМОСТЬ</b>\n\n"
        "Укажите цену в сомах. Если готовы торговаться, можете дописать «торг уместен».\n\n"
        "📖 <b>Пример:</b> <i>2500 сом</i>"
    )
    await update.message.reply_text(text, parse_mode='HTML')
    return PRICE

async def post_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    text = (
        "<b>📱 ШАГ 8 из 8: КОНТАКТЫ</b>\n\n"
        "Введите ваш действующий номер WhatsApp для связи покупателей с вами.\n\n"
        "📖 <b>Пример:</b> <i>+996 700 12 34 56</i>"
    )
    await update.message.reply_text(text, parse_mode='HTML')
    return WHATSAPP

async def post_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id = update.effective_user.id
    context.user_data['whatsapp'] = update.message.text
    city_key = context.user_data['city_key']
    
    db[u_id] = {
        'flowers': context.user_data['flowers'], 'price': context.user_data['price'],
        'date': context.user_data['date'], 'whatsapp': context.user_data['whatsapp'],
        'address': context.user_data['address'], 'city_key': city_key, 
        'cat_key': context.user_data['cat_key'], 'photo': context.user_data['photo']
    }
    
    caption = format_caption(db[u_id])
    kb = [[InlineKeyboardButton("ОДОБРИТЬ ✅", callback_data=f"adm_pub_{u_id}"), 
           InlineKeyboardButton("ОТКЛОНИТЬ ❌", callback_data=f"adm_rej_{u_id}")]]
    
    await context.bot.send_photo(
        ADMIN_ID, context.user_data['photo'], 
        caption=f"📑 <b>НОВАЯ ЗАЯВКА НА ПРОВЕРКУ</b>\n\n{caption}\n👤 От: @{update.effective_user.username}", 
        reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
    )
    
    await update.message.reply_text(
        "✅ <b>ВАША ЗАЯВКА ПРИНЯТА!</b>\n\n"
        "Объявление отправлено модератору на проверку. Мы пришлем вам уведомление о публикации."
        + FOOTER_CMD, parse_mode='HTML'
    )
    return ConversationHandler.END

# --- ПОДДЕРЖКА ---

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_support_chat
    u_id = update.effective_user.id
    if u_id == ADMIN_ID:
        status = f"Активен: <code>{active_support_chat}</code>" if active_support_chat else "Активных нет"
        await update.message.reply_text(f"👨‍💻 <b>АДМИН</b>\n\n{status}\nВ очереди: <b>{len(support_queue)}</b>", parse_mode='HTML')
        return
    if active_support_chat == u_id:
        await update.message.reply_text("🤝 Вы уже в чате с модератором!" + FOOTER_CMD, parse_mode='HTML')
        return
    if active_support_chat is None:
        active_support_chat = u_id
        kb = ReplyKeyboardMarkup([['/endsupport']], resize_keyboard=True)
        await update.message.reply_text(
            "🤝 <b>ЧАТ С ПОДДЕРЖКОЙ ОТКРЫТ!</b>\n\n"
            "Пожалуйста, опишите вашу проблему. Модератор ответит вам здесь.\n"
            "Для выхода нажмите /endsupport", reply_markup=kb, parse_mode='HTML')
        await context.bot.send_message(ADMIN_ID, f"🆘 <b>ЗАПРОС В SUPPORT:</b> @{update.effective_user.username}")
    else:
        if u_id not in support_queue: support_queue.append(u_id)
        await update.message.reply_text(f"⏳ <b>МОДЕРАТОР ЗАНЯТ.</b> Ваше место в очереди: <b>{list(support_queue).index(u_id)+1}</b>" + FOOTER_CMD, parse_mode='HTML')

async def end_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_support_chat
    u_id = update.effective_user.id
    if active_support_chat:
        target = active_support_chat if u_id == ADMIN_ID else ADMIN_ID
        try: await context.bot.send_message(target, "🏁 <b>ЧАТ ЗАВЕРШЕН.</b>\nСпасибо за обращение!", reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        except: pass
    if u_id == ADMIN_ID: await update.message.reply_text(f"🔒 Чат с {active_support_chat} закрыт.")
    else: await update.message.reply_text("🏁 Чат закрыт." + FOOTER_CMD, reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
    active_support_chat = None
    if support_queue:
        next_u = support_queue.popleft()
        active_support_chat = next_u
        await context.bot.send_message(next_u, "✨ <b>ВАША ОЧЕРЕДЬ!</b>\nМодератор подключился. Задавайте ваш вопрос.", reply_markup=ReplyKeyboardMarkup([['/endsupport']], resize_keyboard=True), parse_mode='HTML')
        await context.bot.send_message(ADMIN_ID, f"🔔 Чат открыт с ID <code>{next_u}</code>", parse_mode='HTML')

async def message_relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_support_chat
    u_id = update.effective_user.id
    msg = update.message.text
    if u_id == ADMIN_ID:
        if context.bot_data.get('wait_rej'):
            target = context.bot_data['wait_rej']
            await context.bot.send_message(target, f"💬 <b>ОТВЕТ МОДЕРАТОРА:</b>\n\n{msg}\n\n<i>Вы можете исправить заявку или подать новую через /post</i>", parse_mode='HTML')
            await update.message.reply_text("✅ Отправлено пользователю.")
            context.bot_data['wait_rej'] = None
            return
        if active_support_chat: await context.bot.send_message(active_support_chat, f"👨‍💻 <b>ОТВЕТ МОДЕРАТОРА:</b>\n\n{msg}" + FOOTER_CMD, parse_mode='HTML')
    elif u_id == active_support_chat:
        await context.bot.send_message(ADMIN_ID, f"👤 <b>ОТ @{update.effective_user.username}:</b>\n\n{msg}", parse_mode='HTML')

# --- РЕДАКТИРОВАНИЕ (ИСПРАВЛЕНО) ---

async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    u_id = int(query.data.split("_")[2])
    kb = [
        [InlineKeyboardButton("💰 ЦЕНУ", callback_data=f"edf_price_{u_id}"), InlineKeyboardButton("🕒 ВРЕМЯ", callback_data=f"edf_date_{u_id}")],
        [InlineKeyboardButton("🎁 НАЗВАНИЕ", callback_data=f"edf_flowers_{u_id}"), InlineKeyboardButton("🏠 АДРЕС", callback_data=f"edf_address_{u_id}")],
        [InlineKeyboardButton("⬅️ НАЗАД", callback_data=f"edf_back_{u_id}")]
    ]
    await query.edit_message_text("⚙️ <b>ЧТО ИЗМЕНИТЬ?</b>\nВыберите поле для редактирования:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    return EDIT_CHOOSE_FIELD

async def edit_field_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    u_id = int(data[2])
    if data[1] == "back":
        await query.edit_message_text("⚙️ <b>УПРАВЛЕНИЕ:</b>", reply_markup=get_control_keyboard(u_id), parse_mode='HTML')
        return ConversationHandler.END
    context.user_data['edit_f'], context.user_data['edit_id'] = data[1], u_id
    await query.edit_message_text("📝 <b>ВВЕДИТЕ НОВОЕ ЗНАЧЕНИЕ:</b>", parse_mode='HTML')
    return EDIT_INPUT_VALUE

async def edit_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val, u_id, field = update.message.text, context.user_data['edit_id'], context.user_data['edit_f']
    if u_id in db:
        db[u_id][field] = val
        p = db[u_id]
        await context.bot.edit_message_caption(chat_id=p['c_id'], message_id=p['m_id'], caption=format_caption(p), parse_mode='HTML')
        await update.message.reply_text("✅ <b>ДАННЫЕ ОБНОВЛЕНЫ!</b>", reply_markup=get_control_keyboard(u_id), parse_mode='HTML')
    return ConversationHandler.END

# --- CALLBACKS ---

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    await query.answer()

    if data[0] == "adm" and data[1] == "pub":
        u_id = int(data[2])
        if u_id in db:
            p = db[u_id]
            cfg = CHANNELS_CONFIG[p['city_key']]
            try:
                # В КАНАЛ УХОДИТ ЧИСТЫЙ ТЕКСТ
                res = await context.bot.send_photo(
                    chat_id=cfg['channel_id'], photo=p['photo'], 
                    caption=format_caption(p), 
                    message_thread_id=cfg['categories'][p['cat_key']][1], parse_mode='HTML'
                )
                db[u_id]['m_id'], db[u_id]['c_id'] = res.message_id, cfg['channel_id']
                await context.bot.send_message(u_id, "🎉 <b>ВАШЕ ОБЪЯВЛЕНИЕ ОПУБЛИКОВАНО!</b>\nТеперь вы можете управлять им через меню ниже.", reply_markup=get_control_keyboard(u_id), parse_mode='HTML')
                await query.edit_message_caption(query.message.caption + "\n\n✅ <b>ОПУБЛИКОВАНО</b>", parse_mode='HTML')
            except Exception as e: await query.message.reply_text(f"❌ Ошибка публикации: {e}")

    elif data[0] == "adm" and data[1] == "rej":
        u_id = int(data[2])
        context.bot_data['wait_rej'] = u_id
        await context.bot.send_message(u_id, "❌ <b>ЗАЯВКА ОТКЛОНЕНА МОДЕРАТОРОМ.</b>\nСейчас вам напишут причину.", parse_mode='HTML')
        await query.edit_message_caption(query.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>", parse_mode='HTML')
        await context.bot.send_message(ADMIN_ID, "Напишите причину отклонения:")

    elif data[0] == "usr" and data[1] == "sold":
        u_id = int(data[2])
        if u_id in db:
            p = db[u_id]
            await context.bot.edit_message_caption(chat_id=p['c_id'], message_id=p['m_id'], caption=format_caption(p, True), parse_mode='HTML')
            await query.edit_message_text("✅ <b>ТОВАР ОТМЕЧЕН КАК ПРОДАННЫЙ.</b>")

# --- ЗАПУСК ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Регистрация /post (группа 1)
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler('post', post_start, filters.ChatType.PRIVATE)],
        states={
            CITY: [CallbackQueryHandler(post_city)], 
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_address)],
            PHOTO: [MessageHandler(filters.PHOTO, post_photo)], 
            CATEGORY: [CallbackQueryHandler(post_category)], 
            FLOWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_flowers)], 
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_date)], 
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_price)], 
            WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_whatsapp)],
        }, 
        fallbacks=[CommandHandler('start', start)]
    ), group=1)

    # Регистрация редактирования (группа 2)
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_start, pattern="^usr_edit_")],
        states={ 
            EDIT_CHOOSE_FIELD: [CallbackQueryHandler(edit_field_select, pattern="^edf_")], 
            EDIT_INPUT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_save)] 
        }, 
        fallbacks=[CommandHandler('start', start)]
    ), group=2)

    app.add_handler(CommandHandler('start', start, filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler('support', support_command, filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler('endsupport', end_support, filters.ChatType.PRIVATE))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, message_relay))
    
    print("🚀 БОТ ЗАПУЩЕН! ВСЕ ОШИБКИ ИСПРАВЛЕНЫ.")
    app.run_polling()