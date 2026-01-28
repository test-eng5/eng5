import telebot
from telebot import types

TOKEN = "ВАШ ТОКЕН"
bot = telebot.TeleBot(TOKEN)

BLOCK_WORDS = ['купить', 'продам', 'акция', 'продаю', 'куплю', 'реклама', 'переходи', 'бесплатно', '🔥Горящее предложение!', 'Подарок при заказе 🎁', '🚚 Доставка 🎁 Подарок 💰 Скидка', 'Узнать цену', 'доставка', '❗️', '💲', '🏷️', 'звоните', '8', '+', '7', '₽', 'закажите']
# Используем словарь для хранения количества предупреждений для каждого пользователя
user_warnings = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚫 Антиреклама активна! Сообщения с рекламой удаляются.")

@bot.message_handler(commands=['stats'])
def stats(message):
    """Показать статистику предупреждений"""
    if message.chat.type != "private":  # Только в группах
        if user_warnings:
            stats_text = "📊 Статистика предупреждений:\n"
            for user_id, warnings in list(user_warnings.items()):
                try:
                    user = bot.get_chat_member(message.chat.id, user_id).user
                    username = f"@{user.username}" if user.username else user.first_name
                    stats_text += f"{username}: {warnings} предупреждений\n"
                except:
                    stats_text += f"Пользователь {user_id}: {warnings} предупреждений\n"
        else:
            stats_text = "⚠️ Пока ни у кого нет предупреждений."
        bot.reply_to(message, stats_text)

@bot.message_handler(commands=['warn'])
def warn_user(message):
    """Выдать предупреждение пользователю вручную"""
    if message.chat.type != "private" and message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        username = message.reply_to_message.from_user.username or message.reply_to_message.from_user.first_name
        
        if user_id not in user_warnings:
            user_warnings[user_id] = 0
        
        user_warnings[user_id] += 1
        global warnings
        warnings = user_warnings[user_id]
        
        if warnings >= 3:
            try:
                bot.ban_chat_member(message.chat.id, user_id)
                bot.reply_to(message, f"🚷 @{username} был забанен за 3 предупреждения!")
                user_warnings.pop(user_id)  # Удаляем из статистики
            except Exception as e:
                bot.reply_to(message, f"❌ Не удалось забанить пользователя: {e}")
        else:
            bot.reply_to(message, f"⚠️ @{username}, вам выдано предупреждение! Всего: {warnings}/3")

@bot.message_handler(commands=['unwarn'])
def unwarn_user(message):
    """Снять все предупреждения"""
    if message.chat.type == "private":
        bot.reply_to(message, "❌ Эта команда работает только в группах!")
        return
    
    # Проверяем, является ли отправитель администратором
    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ['administrator', 'creator']:
            bot.reply_to(message, "❌ Только администраторы могут использовать эту команду!")
            return
    except:
        bot.reply_to(message, "❌ Ошибка проверки прав!")
        return
    
    # Очищаем все предупреждения
    global user_warnings
    cleared_count = len(user_warnings)
    user_warnings.clear()
    
    if cleared_count > 0:
        bot.reply_to(message, f"✅ Все предупреждения сняты! Очищено: {cleared_count} записей.")
    else:
        bot.reply_to(message, "ℹ️ Нет активных предупреждений для очистки.")



@bot.message_handler(content_types=['text', 'photo', 'voice'])
def check_ad(message):
    # Получаем текст сообщения
    if message.content_type == 'text':
        text = message.text.lower()
    elif message.content_type == 'photo' and message.caption:
        text = message.caption.lower()
    elif message.content_type == 'voice':
        bot.send_message(message.chat.id, "☢️Включите блокировку голосовых сообщений...☢️")
        return  # Добавляем return чтобы не продолжать выполнение
    else:
        return  # Если нет текста/подписи - выходим
    
    # Дальше идет проверка текста на рекламу
    # text переменная теперь точно существует (для текста и фото с подписью)
    # ... ваш код проверки рекламы ...
    
    # Проверяем на запрещенные слова
    if any(word in text for word in BLOCK_WORDS):
        try:
            # Удаляем сообщение
            bot.delete_message(message.chat.id, message.message_id)
            
            # Отправляем предупреждение
            if message.chat.type == "private":
                warn_text = "❌ Реклама запрещена в личных сообщениях!"
                bot.send_message(message.chat.id, warn_text)
            else:
                user_id = message.from_user.id
                username = message.from_user.username or message.from_user.first_name
                
                # Инициализируем счетчик предупреждений для пользователя
                if user_id not in user_warnings:
                    user_warnings[user_id] = 0
                
                # Увеличиваем счетчик
                user_warnings[user_id] += 1
                warnings = user_warnings[user_id]
                
                # Формируем текст предупреждения
                if warnings == 1:
                    warn_text = f"⚠️ @{username}, реклама запрещена! Первое предупреждение. (1/3)"
                elif warnings == 2:
                    warn_text = f"⚠️ @{username}, реклама запрещена! Второе предупреждение. (2/3)"
                elif warnings >= 3:
                    try:
                        # Блокируем пользователя после 3 предупреждений
                        
                        bot.ban_chat_member(message.chat.id, user_id, until_date=None)
                        warn_text = f"🚷 @{username} был забанен за 3 предупреждения!"
                        # Удаляем из статистики
                        user_warnings.pop(user_id, None)
                    except Exception as e:
                        warn_text = f"❌ Не удалось забанить @{username}. Ошибка: {e}"
                        warnings = 0 
                # Отправляем предупреждение
                sent_msg = bot.send_message(message.chat.id, warn_text)
                
                # Удаляем предупреждение через 10 секунд (опционально)
                # bot.delete_message(message.chat.id, sent_msg.message_id, timeout=10)
                
        except Exception as e:
            print(f"Ошибка при обработке сообщения: {e}")
            # В случае ошибки отправляем сообщение об ошибке только в консоль

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
📋 Доступные команды:
/start - Запустить бота
/help - Показать это сообщение
/stats - Показать статистику предупреждений (только в группах)
/warn - Выдать предупреждение пользователю (ответьте на сообщение)

🔒 Автоматически блокирует сообщения с такими словами:
"""
    help_text += ", ".join(BLOCK_WORDS)
    bot.reply_to(message, help_text)

# Функция для очистки старых записей (опционально)
def cleanup_old_warnings():
    """Очистить старые записи о предупреждениях"""
    # Можно добавить логику очистки по времени
    pass

if __name__ == "__main__":
    print("🚀 Бот-блокировщик рекламы запущен!")
    print("📱 Используйте команды /start и /help для начала работы")
    try:
        bot.polling(none_stop=True, interval=0)
    except Exception as e:

        print(f"❌ Ошибка при запуске бота: {e}")

