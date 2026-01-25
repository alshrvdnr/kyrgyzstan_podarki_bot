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

CITY, PHOTO, CATEGORY, FLOWERS, DATE, PRICE, WHATSAPP = range(7)
SUPPORTING = 8
EDIT_CHOOSE_FIELD, EDIT_INPUT_VALUE = range(9, 11)

logging.basicConfig(level=logging.INFO)

db = {} 
active_support_chat = None # ID пользователя в текущем чате
support_queue = deque()    # Очередь из ID пользователей

# --- ДИЗАЙН ТЕКСТА ---

def format_caption(data, is_sold=False):
    f = html.escape(str(data.get('flowers', '—')))
    p = html.escape(str(data.get('price', '—')))
    d = html.escape(str(data.get('date', '—')))
    c = html.escape(str(data.get('city_name', '—')))
    w = html.escape(str(data.get('whatsapp', '—')))

    if is_sold:
        return f"<b>✅ СТАТУС: ПРОДАНО / НЕАКТУАЛЬНО</b>\n\n🏷 <b>ТОВАР:</b> {f}\n💰 <b>ЦЕНА:</b> {p}"
    
    return (
        f"🏷 <b>ТОВАР:</b> {f}\n\n"
        f"💰 <b>ЦЕНА:</b> {p}\n"
        f"🕒 <b>ВРЕМЯ:</b> {d}\n"
        f"📍 <b>ГОРОД:</b> {c}\n"
        f"📞 <b>НОМЕР:</b> {w}"
    )

def get_control_keyboard(u_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 ИЗМЕНИТЬ ДАННЫЕ", callback_data=f"usr_edit_{u_id}")],
        [InlineKeyboardButton("✅ ТОВАР ПРОДАН", callback_data=f"usr_sold_{u_id}")]
    ])

# --- ПРИВЕТСТВИЕ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🇰🇬 <b>ДОБРО ПОЖАЛОВАТЬ В СЕРВИС «КЫРГЫЗСТАН ПОДАРКИ»!</b>\n\n"
        "Мы поможем вам продать товар быстро. Создайте объявление и управляйте им прямо здесь.\n\n"
        "🚀 <b>КОМАНДЫ:</b>\n"
        "• /post — Создать объявление\n"
        "• /support — Чат с модератором"
    )
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=ReplyKeyboardRemove())

# --- СОЗДАНИЕ ПОСТА (/post) ---

async def post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton(v['name'], callback_data=f"city_{k}")] for k, v in CHANNELS_CONFIG.items()]
    await update.message.reply_text("📍 ШАГ 1: Выберите город:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    return CITY

async def post_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['city_key'] = query.data.replace("city_", "")
    await query.edit_message_text("📸 ШАГ 2: Отправьте фото:")
    return PHOTO

async def post_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo: return PHOTO
    context.user_data['photo'] = update.message.photo[-1].file_id
    city = context.user_data['city_key']
    kb = [[InlineKeyboardButton(n, callback_data=f"cat_{k}")] for k, (n, tid) in CHANNELS_CONFIG[city]['categories'].items()]
    await update.message.reply_text("📁 ШАГ 3: Выберите категорию:", reply_markup=InlineKeyboardMarkup(kb))
    return CATEGORY

async def post_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['cat_key'] = query.data.replace("cat_", "")
    await query.edit_message_text("📝 ШАГ 4: Название товара:")
    return FLOWERS

async def post_flowers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['flowers'] = update.message.text
    await update.message.reply_text("🕒 ШАГ 5: Когда куплен?")
    return DATE

async def post_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date'] = update.message.text
    await update.message.reply_text("💰 ШАГ 6: Цена:")
    return PRICE

async def post_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("📱 ШАГ 7: Номер телефона:")
    return WHATSAPP

async def post_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id = update.effective_user.id
    context.user_data['whatsapp'] = update.message.text
    city_key = context.user_data['city_key']
    db[u_id] = {
        'flowers': context.user_data['flowers'], 'price': context.user_data['price'],
        'date': context.user_data['date'], 'whatsapp': context.user_data['whatsapp'],
        'city_name': CHANNELS_CONFIG[city_key]['name'], 'city_key': city_key, 'cat_key': context.user_data['cat_key']
    }
    caption = format_caption(db[u_id])
    kb = [[InlineKeyboardButton("ОДОБРИТЬ ✅", callback_data=f"adm_pub_{u_id}"), InlineKeyboardButton("ОТКЛОНИТЬ ❌", callback_data=f"adm_rej_{u_id}")]]
    await context.bot.send_photo(ADMIN_ID, context.user_data['photo'], caption=f"📑 <b>НОВАЯ ЗАЯВКА</b>\n\n{caption}", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    await update.message.reply_text("✅ Отправлено модератору.")
    return ConversationHandler.END

# --- ПОДДЕРЖКА (ЧАТ С ОЧЕРЕДЬЮ) ---

async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_support_chat
    u_id = update.effective_user.id
    kb = ReplyKeyboardMarkup([['/endsupport']], resize_keyboard=True)
    
    if u_id == ADMIN_ID:
        if active_support_chat:
            await update.message.reply_text(f"🤝 <b>ЧАТ С ID {active_support_chat} ОТКРЫТ.</b>", reply_markup=kb, parse_mode='HTML')
            return SUPPORTING
        else:
            await update.message.reply_text("⚠️ Активных чатов нет. В очереди: " + str(len(support_queue)), reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    
    # Логика для пользователя
    if active_support_chat == u_id:
        await update.message.reply_text("🤝 Вы уже в чате. Пишите!", reply_markup=kb)
        return SUPPORTING
    
    if active_support_chat is None:
        active_support_chat = u_id
        await update.message.reply_text("🤝 <b>ЧАТ С МОДЕРАТОРОМ ОТКРЫТ</b>\nПишите ваш вопрос. Кнопка завершения внизу. /endsupport", reply_markup=kb, parse_mode='HTML')
        await context.bot.send_message(ADMIN_ID, f"🆘 НОВЫЙ ЧАТ: @{update.effective_user.username}\nВведите /endsupport чтобы zavershity.")
        return SUPPORTING
    else:
        if u_id not in support_queue:
            support_queue.append(u_id)
        pos = list(support_queue).index(u_id) + 1
        await update.message.reply_text(f"⏳ Модератор сейчас занят. Вы добавлены в очередь.\n<b>Ваше место: {pos}</b>", parse_mode='HTML')
        await context.bot.send_message(ADMIN_ID, f"🔔 В очередь встал @{update.effective_user.username}. Всего в очереди: {len(support_queue)}")
        return ConversationHandler.END # Выходим, чтобы не перехватывать сообщения пока не наступит очередь

async def support_relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_support_chat
    u_id, msg = update.effective_user.id, update.message.text
    if msg == "/endsupport": return await end_support(update, context)

    if u_id == ADMIN_ID:
        if active_support_chat:
            await context.bot.send_message(active_support_chat, f"👨‍💻 <b>ОТВЕТ МОДЕРАТОРА:</b>\n{msg}", parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Нет активного чата.")
    else:
        # Только если этот пользователь сейчас активен в чате
        if active_support_chat == u_id:
            await context.bot.send_message(ADMIN_ID, f"👤 СООБЩЕНИЕ ОТ {u_id}:\n{msg}")
    return SUPPORTING

async def end_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_support_chat
    u_id = update.effective_user.id
    
    if active_support_chat:
        target = active_support_chat if u_id == ADMIN_ID else ADMIN_ID
        try:
            await context.bot.send_message(target, "🏁 <b>ЧАТ ЗАВЕРШЕН.</b>", parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
        except: pass
    
    await update.message.reply_text("🏁 ВЫ ВЫШЛИ ИЗ ЧАТА.", reply_markup=ReplyKeyboardRemove())
    
    # Берем следующего из очереди
    active_support_chat = None
    if support_queue:
        next_u = support_queue.popleft()
        active_support_chat = next_u
        kb = ReplyKeyboardMarkup([['/endsupport']], resize_keyboard=True)
        await context.bot.send_message(next_u, "✨ <b>ВАША ОЧЕРЕДЬ!</b>\nМодератор освободился и готов к общению.", reply_markup=kb, parse_mode='HTML')
        await context.bot.send_message(ADMIN_ID, f"🔔 Чат автоматически открыт с ID {next_u}. В очереди осталось: {len(support_queue)}")
    
    return ConversationHandler.END

# --- CALLBACKS И ОТКЛОНЕНИЕ ---

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    await query.answer()

    if data[0] == "adm" and data[1] == "pub":
        u_id = int(data[2])
        if u_id in db:
            p = db[u_id]
            cfg = CHANNELS_CONFIG[p['city_key']]
            msg = await context.bot.copy_message(chat_id=cfg['channel_id'], from_chat_id=query.message.chat.id, message_id=query.message.message_id, message_thread_id=cfg['categories'][p['cat_key']][1])
            db[u_id]['m_id'], db[u_id]['c_id'] = msg.message_id, cfg['channel_id']
            await context.bot.send_message(u_id, "🎉 <b>ОПУБЛИКОВАНО!</b>", reply_markup=get_control_keyboard(u_id), parse_mode='HTML')
            await query.edit_message_caption(query.message.caption + "\n\n✅ ОПУБЛИКОВАНО", parse_mode='HTML')

    elif data[0] == "adm" and data[1] == "rej":
        u_id = int(data[2])
        await context.bot.send_message(u_id, "❌ <b>ВАША ЗАЯВКА ОТКЛОНЕНА МОДЕРАТОРОМ.</b>", parse_mode='HTML')
        context.bot_data['wait_rej'] = u_id
        await query.edit_message_caption(query.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>", parse_mode='HTML')
        await context.bot.send_message(ADMIN_ID, "Напишите причину (она будет отправлена отдельным сообщением):")

    elif data[0] == "usr" and data[1] == "sold":
        u_id = int(data[2])
        if u_id in db:
            p = db[u_id]
            await context.bot.edit_message_caption(chat_id=p['c_id'], message_id=p['m_id'], caption=format_caption(p, True), parse_mode='HTML')
            await query.edit_message_text("✅ ПРОДАНО. Кнопки удалены.")
            del db[u_id]

    elif data[0] == "usr" and data[1] == "edit":
        u_id = int(data[2])
        kb = [[InlineKeyboardButton("💰 ЦЕНУ", callback_data=f"edf_price_{u_id}"), InlineKeyboardButton("🕒 ВРЕМЯ", callback_data=f"edf_date_{u_id}")],
              [InlineKeyboardButton("🎁 НАЗВАНИЕ", callback_data=f"edf_flowers_{u_id}")],
              [InlineKeyboardButton("⬅️ НАЗАД", callback_data=f"edf_back_{u_id}")]]
        await query.edit_message_text("⚙️ Что изменить?", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        return EDIT_CHOOSE_FIELD

async def edit_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    if data[1] == "back":
        await query.edit_message_text("⚙️ УПРАВЛЕНИЕ:", reply_markup=get_control_keyboard(int(data[2])), parse_mode='HTML')
        return ConversationHandler.END
    context.user_data['f'], context.user_data['id'] = data[1], int(data[2])
    await query.edit_message_text("📝 Введите новое значение:")
    return EDIT_INPUT_VALUE

async def edit_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val, u_id, field = update.message.text, context.user_data['id'], context.user_data['f']
    if u_id in db:
        db[u_id][field] = val
        p = db[u_id]
        await context.bot.edit_message_caption(chat_id=p['c_id'], message_id=p['m_id'], caption=format_caption(p), parse_mode='HTML')
        await update.message.reply_text("✅ ОБНОВЛЕНО!", reply_markup=get_control_keyboard(u_id))
    return ConversationHandler.END

async def global_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id = update.effective_user.id
    if u_id == ADMIN_ID:
        if context.bot_data.get('wait_rej'):
            target_u_id = context.bot_data['wait_rej']
            await context.bot.send_message(target_u_id, f"💬 <b>КОММЕНТАРИЙ МОДЕРАТОРА:</b>\n{update.message.text}", parse_mode='HTML')
            await update.message.reply_text("✅ Причина отправлена.")
            context.bot_data['wait_rej'] = None
            return
        if active_support_chat:
             await context.bot.send_message(active_support_chat, f"👨‍💻 <b>ОТВЕТ МОДЕРАТОРА:</b>\n{update.message.text}", parse_mode='HTML')

# --- ЗАПУСК ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    # Поддержка
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler('support', support_start)],
        states={ SUPPORTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_relay)] },
        fallbacks=[CommandHandler('endsupport', end_support)]
    ))

    # Пост
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler('post', post_start)],
        states={
            CITY: [CallbackQueryHandler(post_city)], PHOTO: [MessageHandler(filters.PHOTO, post_photo)],
            CATEGORY: [CallbackQueryHandler(post_category)], FLOWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_flowers)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_date)], PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_price)],
            WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_whatsapp)],
        }, fallbacks=[CommandHandler('start', start)]
    ))

    # Редакт
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callbacks, pattern="^usr_edit_")],
        states={ EDIT_CHOOSE_FIELD: [CallbackQueryHandler(edit_select)], EDIT_INPUT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_save)] },
        fallbacks=[CommandHandler('start', start)]
    ))

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('endsupport', end_support))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), global_msg_handler))
    
    print("🚀 БОТ ЗАПУЩЕН! ШАГИ БЕЗ BOLD, ПОДДЕРЖКА С ОЧЕРЕДЬЮ.")
    app.run_polling()