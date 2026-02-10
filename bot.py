import logging
import html
import time
from collections import deque
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)

# --- 1. НАСТРОЙКИ ---
TOKEN = "8399814024:AAEla8xBVk_9deHydJV0hrc5QYDyXAFpZ8k" 
ADMIN_ID = 1615492914
TEST_MODE = False  # ТЕПЕРЬ ОТКЛЮЧЕНО - РАБОТАЕТ В РЕАЛЬНЫЕ КАНАЛЫ

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
}
EXTRA_FLOWERS_CHANNEL = -1002930228617 # Bishkek Flowers (ПЕРЕПРОДАЖА)

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
        'wait': "✅ <b>Принято!</b> Ваша заявка отправлена модератору.",
        'rejected': "❌ <b>Заявка отклонена.</b>",
        'reason_prefix': "📝 <b>Причина:</b> ",
        'support_open': "🤝 <b>ЧАТ ОТКРЫТ</b>\nПишите сообщение. Модератор ответит здесь.",
        'chat_finished': "🏁 Чат завершен.",
        'edit_menu': "⚙️ <b>ЧТО ИЗМЕНИТЬ?</b>",
        'field_flowers': "📝 Название",
        'field_price': "💰 Цена",
        'field_address': "📍 Адрес",
        'field_whatsapp': "📞 WhatsApp",
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
        'wait': "✅ <b>Кабыл алынды!</b> Текшерүүгө жөнөтүлдү.",
        'rejected': "❌ <b>Жарыя четке кагылды.</b>",
        'reason_prefix': "📝 <b>Себеби:</b> ",
        'support_open': "🤝 <b>ЧАТ АЧЫЛДЫ</b>\nЖазыңыз, модератор жооп берет.",
        'chat_finished': "🏁 Чат аяктады.",
        'edit_menu': "⚙️ <b>ЭМНЕНИ ӨЗГӨРТҮҮ КЕРЕК?</b>",
        'field_flowers': "📝 Аталышы",
        'field_price': "💰 Баасы",
        'field_address': "📍 Дарек",
        'field_whatsapp': "📞 WhatsApp",
        'cats': {"flowers": "Гүлдөр 🌸", "jewelry": "Зергер буюмдар 💎", "gifts": "Белектер 🎁", "certs": "Сертификаттар 🎟"}
    }
}

db_ads, db_users = {}, {}
active_support_chat = None 
support_queue = deque()

PHOTO, CITY, ADDRESS, CATEGORY, FLOWERS, DATE, PRICE, WHATSAPP = range(8)

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
        except:
            pass

# --- ГЛАВНЫЕ КОМАНДЫ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id = update.effective_user.id
    context.user_data.clear()
    
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
        await update.callback_query.message.edit_text(s['welcome'], reply_markup=kb, parse_mode='HTML')
    else:
        msg = await update.message.reply_text(s['welcome'], reply_markup=kb, parse_mode='HTML')
        context.user_data['last_msg'] = msg.message_id
    return ConversationHandler.END

async def admin_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(f"📊 Юзеров: {len(db_users)}\nЗаявок: {len(db_ads)}\nЧат-очередь: {len(support_queue)}")

async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    db_users[query.from_user.id] = query.data.split("_")[1]
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
    if query.data.startswith("city_"):
        context.user_data['city_key'] = query.data.replace("city_", "")
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
    if query.data.startswith("cat_"):
        context.user_data['cat_key'] = query.data.replace("cat_", "")
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
    ad_id = str(int(time.time()))
    
    db_ads[ad_id] = {
        'user_id': u_id, 'city_key': context.user_data['city_key'], 'cat_key': context.user_data['cat_key'],
        'flowers': context.user_data['flowers'], 'price': context.user_data['price'], 'date': context.user_data['date'],
        'address': context.user_data['address'], 'whatsapp': context.user_data['whatsapp'], 'photos': context.user_data['photos']
    }
    
    await clear_ui(update, context)
    
    # Модерация (Админу)
    ad = db_ads[ad_id]
    adm_cap = f"📑 <b>ЗАЯВКА</b>\n👤 @{update.effective_user.username}\n📍 {CHANNELS_CONFIG[ad['city_key']]['name']} | {STRINGS['ru']['cats'][ad['cat_key']]}\n\n{format_caption(ad)}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("ОДОБРИТЬ ✅", callback_data=f"apub_{ad_id}"), InlineKeyboardButton("ОТКЛОНИТЬ ❌", callback_data=f"arej_{ad_id}")],
        [InlineKeyboardButton("⚙️ КАТЕГОРИЯ", callback_data=f"achg_{ad_id}")]
    ])
    await context.bot.send_photo(ADMIN_ID, ad['photos'][0], caption=adm_cap, reply_markup=kb, parse_mode='HTML')
    
    await update.message.reply_text(STRINGS[lang]['wait'], parse_mode='HTML')
    return ConversationHandler.END

# --- АДМИН ---

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
            # 1. Основной канал
            if len(ad['photos']) == 1:
                msg = await context.bot.send_photo(target, ad['photos'][0], caption=cap, parse_mode='HTML', message_thread_id=thread)
            else:
                media = [InputMediaPhoto(ad['photos'][0], caption=cap, parse_mode='HTML')]
                for ph in ad['photos'][1:10]: media.append(InputMediaPhoto(ph))
                msgs = await context.bot.send_media_group(target, media, message_thread_id=thread)
                msg = msgs[0]
            db_ads[ad_id].update({'m_id': msg.message_id, 'c_id': target})

            # 2. Доп канал (Цветы Бишкек)
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
        # Сразу уведомляем
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
    if active_support_chat == u_id: return
    
    await update.callback_query.answer()
    if active_support_chat is None:
        active_support_chat = u_id
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(STRINGS[lang]['btn_finish_chat'], callback_data="finish_chat")]])
        await context.bot.send_message(u_id, STRINGS[lang]['support_open'], reply_markup=kb, parse_mode='HTML')
        await context.bot.send_message(ADMIN_ID, f"🆘 ЧАТ: @{update.effective_user.username}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏁 ЗАВЕРШИТЬ", callback_data="finish_chat")]]))
    else:
        if u_id not in support_queue: support_queue.append(u_id)
        await update.callback_query.message.reply_text(f"Вы в очереди: {list(support_queue).index(u_id)+1}")

async def finish_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_support_chat
    await update.callback_query.answer()
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
    else:
        if update.effective_user.id == ADMIN_ID:
            try: await update.callback_query.message.edit_text("🏁 Все чаты закрыты.")
            except: pass

# --- ИЗМЕНЕНИЕ ---

async def user_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    action, ad_id = data[0], data[1]
    ad = db_ads.get(ad_id)
    if not ad: return
    lang = db_users.get(update.effective_user.id, 'ru')

    if action == "usold":
        # Синхронно в двух каналах
        for m_key, c_key in [('m_id', 'c_id'), ('ex_m_id', 'ex_c_id')]:
            if m_key in ad:
                try: await context.bot.edit_message_caption(chat_id=ad[c_key], message_id=ad[m_key], caption=format_caption(ad, True), parse_mode='HTML')
                except: pass
        await query.edit_message_text("✅ ТОВАР ПРОДАН")

    elif action == "uedit":
        s = STRINGS[lang]
        kb = [[InlineKeyboardButton(s['field_flowers'], callback_data=f"uf_flowers_{ad_id}"), InlineKeyboardButton(s['field_price'], callback_data=f"uf_price_{ad_id}")],
              [InlineKeyboardButton(s['field_address'], callback_data=f"uf_address_{ad_id}"), InlineKeyboardButton(s['field_whatsapp'], callback_data=f"uf_whatsapp_{ad_id}")],
              [InlineKeyboardButton(s['btn_back'], callback_data=f"uback_{ad_id}")]]
        await query.edit_message_text(s['edit_menu'], reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

    elif action == "uback":
        kb = [[InlineKeyboardButton("📝 Изменить", callback_data=f"uedit_{ad_id}"), InlineKeyboardButton("✅ Продано", callback_data=f"usold_{ad_id}")]]
        await query.edit_message_text("Меню управления:", reply_markup=InlineKeyboardMarkup(kb))

# --- РЕЛЕЙ ---

async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id, text = update.effective_user.id, update.message.text
    
    # 1. Редактирование (Синхронно)
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

    # 2. Причина отказа
    if u_id == ADMIN_ID and context.bot_data.get('wait_rej'):
        target = context.bot_data['wait_rej']
        lang = db_users.get(target, 'ru')
        await context.bot.send_message(target, f"{STRINGS[lang]['reason_prefix']}{text}", parse_mode='HTML')
        context.bot_data['wait_rej'] = None
        await update.message.reply_text("Причина отправлена.")
        return

    # 3. Чат
    if u_id == ADMIN_ID and active_support_chat: await context.bot.send_message(active_support_chat, f"👨‍💻 {text}")
    elif u_id == active_support_chat: await context.bot.send_message(ADMIN_ID, f"👤 {text}")

async def field_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; _, field, ad_id = query.data.split("_")
    context.user_data['edit_field'], context.user_data['edit_ad_id'] = field, ad_id
    await query.answer(); await query.edit_message_text("✍️ Введите новое значение:")

# --- ЗАПУСК ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('infa', admin_info))
    app.add_handler(CallbackQueryHandler(set_lang, pattern="^sl_"))
    app.add_handler(CallbackQueryHandler(admin_decision, pattern="^apub_|^arej_|^achg_"))
    app.add_handler(CallbackQueryHandler(admin_set_category, pattern="^asetcat_"))
    app.add_handler(CallbackQueryHandler(user_actions, pattern="^usold_|^uedit_|^uback_"))
    app.add_handler(CallbackQueryHandler(field_select, pattern="^uf_"))
    app.add_handler(CallbackQueryHandler(start, pattern="^to_main$"))
    
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
        }, fallbacks=[CommandHandler('start', start)]
    ))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay))
    app.run_polling()