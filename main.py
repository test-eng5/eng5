import telebot
import time 

TOKEN = " token"
bot = telebot.TeleBot(TOKEN)

BLOCK_WORDS = ['купить', 'продам', 'акция', 'продаю', 'куплю', 'реклама', 'переходи', 
               'бесплатно', 'доставка', 'звоните', 'закажите', '🔥', '🎁', '🚚', '💰', '❗️', '💲', '🏷️', '₽']

user_warnings = {}

def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚫 Антиреклама активна! Используйте /help для справки")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    help_text = """📋 Команды:
/help - справка
/stats - статистика предупреждений
/warn - выдать предупреждение (ответьте на сообщение)
/unwarn - снять предупреждения (админы)

🔒 Блокирует: рекламу, спам, ссылки (кроме github, youtube, vk), CAPS LOCK"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.chat.type == "private":  
        return bot.reply_to(message, "❌ Только в группах!")
    
    if not user_warnings:
        return bot.reply_to(message, "⚠️ Предупреждений нет.")
    
    stats_text = "📊 Статистика:\n"
    for user_id, warnings in user_warnings.items():
        try:
            user = bot.get_chat_member(message.chat.id, user_id).user
            name = f"@{user.username}" if user.username else user.first_name
            stats_text += f"{name}: {warnings}\n"
        except:
            stats_text += f"ID {user_id}: {warnings}\n"
    bot.reply_to(message, stats_text)

@bot.message_handler(commands=['warn'])
def warn_user(message):
    if message.chat.type == "private" or not message.reply_to_message:
        return bot.reply_to(message, "❌ Ответьте на сообщение в группе!")
    
    user_id = message.reply_to_message.from_user.id
    name = message.reply_to_message.from_user.first_name
    
    user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
    warnings = user_warnings[user_id]
    
    if warnings >= 3:
        try:
            bot.ban_chat_member(message.chat.id, user_id)
            bot.reply_to(message, f"🚷 {name} забанен за 3 предупреждения!")
            user_warnings.pop(user_id)
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка бана: {e}")
    else:
        bot.reply_to(message, f"⚠️ {name}, предупреждение {warnings}/3")

@bot.message_handler(commands=['unwarn'])
def unwarn_user(message):
    if message.chat.type == "private" or not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Только админы в группах!")
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        if user_id in user_warnings:
            warnings = user_warnings.pop(user_id)
            name = message.reply_to_message.from_user.first_name
            bot.reply_to(message, f"✅ Снято {warnings} предупреждений у {name}")
    else:
        count = len(user_warnings)
        user_warnings.clear()
        bot.reply_to(message, f"✅ Снято {count} предупреждений")




last = {} 
@bot.message_handler(func=lambda m: True)
def all_messages(message):
    uid = message.from_user.id
    now = time.time()
    
    if uid in last and now - last[uid] < 3:
        try:
            
            bot.send_message(message.chat.id, "⏳ подождите еще 3 секунды")
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        return
    
    last[uid] = now



@bot.message_handler(content_types=['text', 'photo'])
def check_ad(message):
    if message.text and message.text.startswith('/'):
        return
    
    text = (message.text or message.caption or "").lower()
    
    # Проверка CAPS LOCK
    if len(text) > 10 and sum(1 for c in text if c.isupper()) / len(text) > 0.7:
        bot.delete_message(message.chat.id, message.message_id)
        return
    
    # Проверка ссылок
    if ('http' in text or 't.me/' in text or '.ru' in text or '.com' in text) and \
       not any(site in text for site in ['github.com', 'youtube.com', 'vk.com', 'youtu.be']):
        bot.delete_message(message.chat.id, message.message_id)
        if message.chat.type != "private":
            bot.send_message(message.chat.id, "❌ Ссылки запрещены!")
        return
    
    # Проверка стоп-слов
    for word in BLOCK_WORDS:
        if word.lower() in text:
            bot.delete_message(message.chat.id, message.message_id)
            
            if message.chat.type == "private":
                bot.send_message(message.chat.id, "❌ Реклама запрещена!")
                return
            
            user_id = message.from_user.id
            user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
            warnings = user_warnings[user_id]
            name = message.from_user.first_name
            
            if warnings >= 3:
                try:
                    bot.ban_chat_member(message.chat.id, user_id)
                    bot.send_message(message.chat.id, f"🚷 {name} забанен!")
                    user_warnings.pop(user_id)
                except:
                    pass
            else:
                bot.send_message(message.chat.id, f"⚠️ {name}, реклама запрещена! ({warnings}/3)")
            break






if __name__ == "__main__":
    print("🚀 Бот запущен!")
    bot.polling(none_stop=True)
