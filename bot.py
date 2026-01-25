import logging
import os  # Добавили это (встроенный модуль для работы с системой)
from dotenv import load_dotenv  # Добавили это (чтение .env)
from collections import deque
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)

# Вызываем функцию, которая загрузит данные из файла .env в память
load_dotenv()

# --- 1. НАСТРОЙКИ ---
# Теперь мы НЕ пишем токен цифрами. Мы берем его из переменной BOT_TOKEN
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 1615492914

CHANNELS_CONFIG = {
    "bishkek": {
        "name": "Бишкек Подарки",
        "channel_id": -1003898037632,
        "categories": {
            "flowers": ("🌸 Цветы", 11),
            "jewelry": ("💎 Ювелирка", 12),
            "gifts": ("🎁 Подарки", 13),
            "certs": ("🎟 Сертификаты", 14)
        }
    },
    "osh": {
        "name": "Ош Подарки",
        "channel_id": -1003840234187,
        "categories": {
            "flowers": ("🌸 Цветы", 4),
            "jewelry": ("💎 Ювелирка", 6),
            "gifts": ("🎁 Подарки", 5),
            "certs": ("🎟 Сертификаты", 30)
        }
    },
    "jalalabad": {
        "name": "Джалал-Абад Подарки",
        "channel_id": -1003764029224,
        "categories": {
            "flowers": ("🌸 Цветы", 4),
            "gifts": ("🎁 Подарки", 5),
            "jewelry": ("💎 Ювелирка", 6),
            "certs": ("🎟 Сертификаты", 7)
        }
    }
}

CITY, PHOTO, CATEGORY, FLOWERS, DATE, PRICE, WHATSAPP = range(7)
SUPPORTING = 8

logging.basicConfig(level=logging.INFO)
support_queue = deque()
current_active_user = None

# --- ГЛАВНОЕ МЕНЮ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 **Здравствуйте! Вы в сервисе перепродажи «Кыргызстан Подарки»** 🇰🇬\n\n"
        "Я помогу вам быстро разместить объявление о продаже вашего букета, ювелирного изделия или сертификата в наших каналах.\n\n"
        "ℹ️ **Доступные команды:**\n"
        "🌹 /post — Начать создание объявления\n"
        "💬 /support — Написать модератору (поддержка)\n"
        "❓ /help — Показать это сообщение снова\n\n"
        "Нажмите /post, чтобы предложить свой товар!"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

# --- ЛОГИКА /POST ---

async def post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📍 Бишкек", callback_data="city_bishkek")],
        [InlineKeyboardButton("📍 Ош", callback_data="city_osh")],
        [InlineKeyboardButton("📍 Джалал-Абад", callback_data="city_jalalabad")]
    ]
    await update.message.reply_text(
        "📍 **Шаг 1 из 7: Выбор региона**\n\nВ каком городе вы хотите опубликовать объявление?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return CITY

async def post_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    city_key = query.data.replace("city_", "")
    context.user_data['city'] = city_key
    await query.edit_message_text(
        f"✅ Выбран город: **{CHANNELS_CONFIG[city_key]['name']}**\n\n"
        "📸 **Шаг 2 из 7: Фотография**\n\nПожалуйста, отправьте ОДНО качественное фото вашего товара. Хорошее освещение поможет продать быстрее!",
        parse_mode='Markdown'
    )
    return PHOTO

async def post_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("⚠️ Пожалуйста, отправьте именно изображение (фотографию).")
        return PHOTO
    context.user_data['photo'] = update.message.photo[-1].file_id
    city = context.user_data['city']
    keyboard = [[InlineKeyboardButton(name, callback_data=f"cat_{id}")] for id, (name, tid) in CHANNELS_CONFIG[city]['categories'].items()]
    await update.message.reply_text(
        "📁 **Шаг 3 из 7: Категория**\n\nВыберите категорию вашего товара из списка ниже:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return CATEGORY

async def post_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['category'] = query.data.replace("cat_", "")
    await query.edit_message_text(
        "📝 **Шаг 4 из 7: Описание**\n\nНапишите краткое название товара.\n"
        "_(Например: Букет из 101 розы или Золотая цепочка)_",
        parse_mode='Markdown'
    )
    return FLOWERS

async def post_flowers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['flowers'] = update.message.text
    await update.message.reply_text(
        "🕒 **Шаг 5 из 7: Состояние/Время**\n\nКогда был куплен или получен товар?\n"
        "_(Например: Сегодня в 10:00, Вчера вечером)_",
        parse_mode='Markdown'
    )
    return DATE

async def post_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date'] = update.message.text
    await update.message.reply_text(
        "💰 **Шаг 6 из 7: Цена**\n\nКакую цену вы устанавливаете в сомах?\n"
        "_(Например: 2500 сом)_",
        parse_mode='Markdown'
    )
    return PRICE

async def post_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text(
        "📱 **Шаг 7 из 7: Контакты**\n\nУкажите ваш номер WhatsApp для связи с покупателем:",
        parse_mode='Markdown'
    )
    return WHATSAPP

async def post_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['whatsapp'] = update.message.text
    user = update.effective_user
    city = context.user_data['city']
    cat = context.user_data['category']
    cat_name = CHANNELS_CONFIG[city]['categories'][cat][0]

    caption = (
        f"📩 **НОВАЯ ЗАЯВКА НА МОДЕРАЦИЮ**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📍 Город: {CHANNELS_CONFIG[city]['name']}\n"
        f"🗂 Категория: {cat_name}\n\n"
        f"🎁 Товар: {context.user_data['flowers']}\n"
        f"🕒 Когда получен: {context.user_data['date']}\n"
        f"💵 Цена: {context.user_data['price']}\n"
        f"📱 WA: {context.user_data['whatsapp']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 Отправитель: @{user.username if user.username else user.first_name}"
    )
    keyboard = [[InlineKeyboardButton("Принять ✅", callback_data=f"pub_{city}_{cat}_{user.id}"),
                 InlineKeyboardButton("Отклонить ❌", callback_data=f"rej_{user.id}")]]

    await context.bot.send_photo(ADMIN_ID, context.user_data['photo'], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    await update.message.reply_text("✨ **Ваша заявка принята!**\n\nОна отправлена на проверку модератору. Мы сообщим вам о результате публикации здесь.")
    return ConversationHandler.END

# --- ЛОГИКА АДМИНА ---

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    
    if data[0] == "pub":
        city_key, cat_key, user_id = data[1], data[2], int(data[3])
        config = CHANNELS_CONFIG[city_key]
        try:
            await context.bot.copy_message(
                chat_id=config['channel_id'],
                from_chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                message_thread_id=config['categories'][cat_key][1]
            )
            await context.bot.send_message(user_id, f"🥳 **Поздравляем!** Ваше объявление одобрено и опубликовано в канале **{config['name']}**!", parse_mode='Markdown')
            await query.edit_message_caption(caption=query.message.caption + "\n\n✅ **СТАТУС: ОПУБЛИКОВАНО**")
        except Exception as e:
            await query.answer(f"Ошибка: {e}", show_alert=True)
    
    elif data[0] == "rej":
        user_id = int(data[1])
        try:
            await context.bot.send_message(user_id, "❌ **К сожалению, ваше объявление отклонено модератором.**", parse_mode='Markdown')
        except: pass
        await query.edit_message_caption(caption=query.message.caption + "\n\n❌ **ОТКЛОНЕНО**")
        context.user_data['waiting_rej_reason'] = user_id
        await query.answer("Отклонено. Напишите причину, если нужно.")
        await context.bot.send_message(ADMIN_ID, "Заявка отклонена. Чтобы отправить пользователю **причину**, напишите её следующим сообщением.")
    await query.answer()

async def handle_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_rej_reason'):
        u_id = context.user_data['waiting_rej_reason']
        reason = update.message.text
        try:
            await context.bot.send_message(u_id, f"💬 **Комментарий модератора по отказу:**\n{reason}", parse_mode='Markdown')
            await update.message.reply_text("✅ Причина успешно отправлена пользователю.")
        except: pass
        context.user_data['waiting_rej_reason'] = None
        return
    await support_chat(update, context)

# --- ПОДДЕРЖКА ---

async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_active_user
    u_id = update.effective_user.id
    if u_id == ADMIN_ID: return 
    if current_active_user is None:
        current_active_user = u_id
        await update.message.reply_text("🤝 **Вы на связи с модератором!**\n\nОпишите ваш вопрос. Чтобы завершить чат, напишите /endsupport.")
        await context.bot.send_message(ADMIN_ID, f"🆘 **Новый чат начат!**\nОт: @{update.effective_user.username}")
    else:
        if u_id not in support_queue: support_queue.append(u_id)
        await update.message.reply_text(f"⏳ Модератор сейчас занят другим пользователем. Вы в очереди: {len(support_queue)}")
    return SUPPORTING

async def support_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_active_user
    u_id = update.effective_user.id
    text = update.message.text
    if text == "/endsupport": return

    if u_id == ADMIN_ID and current_active_user:
        await context.bot.send_message(current_active_user, f"👨‍💻 **Модератор:** {text}")
    elif u_id == current_active_user:
        await context.bot.send_message(ADMIN_ID, f"👤 **Пользователь:** {text}")

async def stop_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_active_user
    u_id = update.effective_user.id
    if u_id == ADMIN_ID or u_id == current_active_user:
        if current_active_user:
            try: await context.bot.send_message(current_active_user, "🏁 **Чат завершен.** Всего доброго!")
            except: pass
        current_active_user = None
        await context.bot.send_message(ADMIN_ID, "🔒 **Чат закрыт.**")
        if support_queue:
            next_u = support_queue.popleft()
            current_active_user = next_u
            await context.bot.send_message(next_u, "✨ **Модератор освободился!** Слушаю вас.")
            await context.bot.send_message(ADMIN_ID, f"🔔 Чат начат с пользователем в очереди: {next_u}")
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    post_handler = ConversationHandler(
        entry_points=[CommandHandler('post', post_start)],
        states={
            CITY: [CallbackQueryHandler(post_city)],
            PHOTO: [MessageHandler(filters.PHOTO, post_photo)],
            CATEGORY: [CallbackQueryHandler(post_category)],
            FLOWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_flowers)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_date)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_price)],
            WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_whatsapp)],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    support_handler = ConversationHandler(
        entry_points=[CommandHandler('support', support_start)],
        states={SUPPORTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_chat)]},
        fallbacks=[CommandHandler('endsupport', stop_support), CommandHandler('start', start)]
    )

    app.add_handler(post_handler)
    app.add_handler(support_handler)
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('endsupport', stop_support))
    app.add_handler(CallbackQueryHandler(admin_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages))
    
    print("Бот «Кыргызстан Подарки» запущен!")
    app.run_polling()