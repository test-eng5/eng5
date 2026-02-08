import telebot
import time
import re


TOKEN = "8508922582:AAGszTmNqjsDJfUP8aajGfoHAG88p-LcmKE"  
bot = telebot.TeleBot(TOKEN)

BLOCK_WORDS = ['купить', 'продам', 'акция', 'продаю', 'куплю', 'реклама', 'переходи', 
               'бесплатно', 'доставка', 'звоните', 'закажите', '🔥', '🎁', '🚚', '💰', '❗️', '💲', '🏷️', '₽', "?", '', "💸", 'вход:', 'получи', 'd o x o d']

ALLOWED_DOMAINS = ['github.com', 'youtube.com', 'vk.com', 'youtu.be']

# Хранилища данных (в реальном боте используйте БД)
user_warnings = {}
user_message_count = {}
flood_cooldown = {}

def is_admin(chat_id, user_id):
    """Проверка, является ли пользователь администратором"""
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        print(f"Ошибка проверки администратора: {e}")
        return False

def check_links(text):
    """Проверка ссылок с использованием регулярных выражений"""
    if not text:
        return True
    
    # Улучшенный паттерн для поиска URL
    url_pattern = r'(?:https?://|www\.|t\.me/|@)[^\s]+'
    urls = re.findall(url_pattern, text.lower())
    
    if not urls:
        return True  # Ссылок нет
    
    # Проверяем каждую ссылку на разрешенные домены
    for url in urls:
        allowed = False
        for domain in ALLOWED_DOMAINS:
            if domain in url:
                allowed = True
                break
        
        if not allowed:
            return False
    
    return True

@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type == "private":
        bot.reply_to(message, "🚫 Антиреклама активна! Используйте /help для справки")
    else:
        bot.reply_to(message, "Бот активен! Используйте /help для списка команд")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    help_text = """📋 Команды:
/help - справка
/stats - статистика предупреждений
/warn - выдать предупреждение (админы, ответьте на сообщение)
/unwarn - снять предупреждения (админы, ответьте на сообщение)
/unwarn_all - снять все предупреждения (админы)

🔒 Блокирует: рекламу, спам, ссылки (кроме github, youtube, vk), CAPS LOCK"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.chat.type == "private":  
        return bot.reply_to(message, "❌ Доступно только в группах!")
    
    if not user_warnings:
        return bot.reply_to(message, "⚠️ Предупреждений нет.")
    
    stats_text = "📊 Статистика предупреждений:\n"
    for user_id, warnings in list(user_warnings.items()):
        try:
            user = bot.get_chat_member(message.chat.id, user_id).user
            name = f"@{user.username}" if user.username else user.first_name
            stats_text += f"{name}: {warnings}/3\n"
        except:
            # Если пользователь не найден, удаляем из статистики
            user_warnings.pop(user_id, None)
    
    bot.reply_to(message, stats_text)

@bot.message_handler(commands=['warn'])
def warn_user(message):
    """Выдать предупреждение пользователю"""
    if message.chat.type == "private":
        return bot.reply_to(message, "❌ Эта команда работает только в группах!")
    
    if not message.reply_to_message:
        return bot.reply_to(message, "❌ Ответьте на сообщение пользователя!")
    
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Только администраторы могут использовать эту команду!")
    
    user_id = message.reply_to_message.from_user.id
    name = message.reply_to_message.from_user.first_name
    

    
    user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
    warnings = user_warnings[user_id]
    
    if warnings >= 3:
        try:
            bot.ban_chat_member(message.chat.id, user_id)
            bot.reply_to(message, f"🚷 {name} забанен за 3 предупреждения!")
            user_warnings.pop(user_id, None)
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка бана: {e}")
    else:
        bot.reply_to(message, f"⚠️ {name}, предупреждение {warnings}/3")

@bot.message_handler(commands=['unwarn'])
def unwarn_user(message):
    """Снять одно предупреждение у пользователя"""
    if message.chat.type == "private":
        return bot.reply_to(message, "❌ Эта команда работает только в группах!")
    
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Только администраторы могут использовать эту команду!")
    
    if not message.reply_to_message:
        return bot.reply_to(message, "❌ Ответьте на сообщение пользователя!")
    
    user_id = message.reply_to_message.from_user.id
    name = message.reply_to_message.from_user.first_name
    
    if user_id in user_warnings:
        user_warnings[user_id] -= 1
        if user_warnings[user_id] <= 0:
            user_warnings.pop(user_id, None)
            bot.reply_to(message, f"✅ Все предупреждения сняты у {name}")
        else:
            bot.reply_to(message, f"✅ Снято одно предупреждение у {name}. Осталось: {user_warnings[user_id]}/3")
    else:
        bot.reply_to(message, f"ℹ️ У {name} нет предупреждений")

@bot.message_handler(commands=['unwarn_all'])
def unwarn_all(message):
    """Снять все предупреждения у всех пользователей"""
    if message.chat.type == "private":
        return bot.reply_to(message, "❌ Эта команда работает только в группах!")
    
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "❌ Только администраторы могут использовать эту команду!")
    
    count = len(user_warnings)
    user_warnings.clear()
    bot.reply_to(message, f"✅ Снято {count} предупреждений у всех пользователей")

def check_flood(user_id, chat_id):
    """Проверка на флуд"""
    current_time = time.time()
    
    # Проверяем глобальный флуд
    if user_id in flood_cooldown:
        if current_time < flood_cooldown[user_id]:
            return False
        else:
            flood_cooldown.pop(user_id, None)
    
    # Уникальный ключ для каждого чата
    key = f"{chat_id}_{user_id}"
    
    # Проверяем частоту сообщений
    if key not in user_message_count:
        user_message_count[key] = {'count': 1, 'first_time': current_time}
        return True
    else:
        user_message_count[key]['count'] += 1
        
        # Если больше 5 сообщений за 10 секунд - мут
        if (user_message_count[key]['count'] >= 5 and 
            current_time - user_message_count[key]['first_time'] <= 10):
            flood_cooldown[user_id] = current_time + 30  # Мут на 30 секунд
            user_message_count.pop(key, None)
            return False
        
        # Сброс счетчика каждые 10 секунд
        if current_time - user_message_count[key]['first_time'] > 10:
            user_message_count[key] = {'count': 1, 'first_time': current_time}
        
        return True

@bot.message_handler(content_types=['text', 'photo', 'document', 'sticker', 'video'])
def check_message(message):
    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        return
    
    # Пропускаем администраторов
    if is_admin(message.chat.id, message.from_user.id):
        return
    
    # Проверка на флуд (только в группах)
    if message.chat.type != "private":
        if not check_flood(message.from_user.id, message.chat.id):
            try:
                bot.delete_message(message.chat.id, message.message_id)
                bot.send_message(message.chat.id, 
                               f"⏳ {message.from_user.first_name}, не флуди!", 
                               reply_to_message_id=message.message_id)
            except Exception as e:
                print(f"Ошибка антифлуда: {e}")
            return
    
    # Получаем текст сообщения
    text = (message.text or message.caption or "").strip()
    text_lower = text.lower()
    
    # Пропускаем пустые сообщения и стикеры
    if not text and message.content_type not in ['sticker', 'photo']:
        return
    
    # Проверка капса (только для текстовых сообщений)
    if text and len(text) > 10:
        letters = [c for c in text if c.isalpha()]
        if letters:
            uppercase_count = sum(1 for c in letters if c.isupper())
            if uppercase_count / len(letters) > 0.7:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    if message.chat.type != "private":
                        bot.send_message(message.chat.id, 
                                       f"❌ {message.from_user.first_name}, слишком много заглавных букв!")
                except Exception as e:
                    print(f"Ошибка при удалении капса: {e}")
                return
    
    # Проверка ссылок
    if text and not check_links(text_lower):
        handle_violation(message, "ссылки запрещены")
        return
    
    # Проверка стоп-слов
    if text:
        for word in BLOCK_WORDS:
            if word and word.lower() in text_lower:
                handle_violation(message, "реклама запрещена")
                return

def handle_violation(message, reason):
    """Обработка нарушений"""
    try:
        # Пытаемся удалить сообщение
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        
        # В личных сообщениях просто отправляем предупреждение
        if message.chat.type == "private":
            bot.send_message(message.chat.id, f"❌ {reason.capitalize()}!")
            return
        
        # В группах добавляем предупреждение
        user_id = message.from_user.id
        name = message.from_user.first_name
        
        user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
        warnings = user_warnings[user_id]
        
        if warnings >= 3:
            try:
                bot.ban_chat_member(message.chat.id, user_id)
                bot.send_message(message.chat.id, f"🚷 {name} забанен за нарушение правил!")
                user_warnings.pop(user_id, None)
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Ошибка бана: {e}")
        else:
            bot.send_message(message.chat.id, 
                           f"⚠️ {name}, {reason}! ({warnings}/3)")
    
    except Exception as e:
        print(f"Ошибка при обработке нарушения: {e}")

# Обработчик для новых участников
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        if new_member.id == bot.get_me().id:
            bot.send_message(message.chat.id, 
                           "привет! Я бот для защиты от рекламы. Добавьте меня в администраторы для полного функционала.")
            return
        
        welcome_text = f" привет, {new_member.first_name}\n"
        welcome_text += " правила\n"

        
        bot.send_message(message.chat.id, welcome_text, ''' 


" запрещена реклама и спам\n"
 " ссылки только на разрешенные ресурсы\n"
 " Не используйте CAPS LOCK\n"
 " Уважайте других участников\n\n"
 "используй /help для списка команд бота"
                         

                            ''' )

if __name__ == "__main__":
    print("работает!")
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
