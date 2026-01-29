import telebot
from telebot import types
import re
import time
from typing import Dict, List
from collections import defaultdict

TOKEN = "TOKEN"
bot = telebot.TeleBot(TOKEN)

# ====================== КОНФИГУРАЦИЯ КЛЮЧЕВЫХ СЛОВ ======================
AD_KEYWORDS = [
    r'купить', r'продам', r'продажа', r'скидк[а-я]*', r'распродаж',
    r'заказ[а-я]*', r'доставк[а-я]*', r'магазин', r'интернет[-\s]*магазин',
    r'бесплатно', r'акци[я-я]*', r'только сегодня', r'выгодно',
    r'реклам[а-я]*', r'объявлени[е-я]*', r'предложени[е-я]*',
    r'спешите', r'ограниченно', r'последни[е-я]*',
    
    # Финансовые мошенничества
    r'кредит[а-я]*', r'займ[а-я]*', r'быстр[а-я]* деньг[а-я]*',
    r'инвестиц[а-я]*', r'крипто', r'bitcoin', r'брокер',
    r'заработ[а-я]*', r'удаленн[а-я]* работ[а-я]*',
    
    # Ссылки
    r'http[s]?://', r'www\.', r't\.me/', r'@[A-Za-z0-9_]{5,}',
    r'(?:https?://)?(?:t\.me/|telegram\.me/)',
    
    # Капс
    r'^[^a-zа-яё]{10,}$',  # Сообщения без строчных букв
    
    r'продаю', r'куплю', r'переходи', r'🔥Горящее предложение!',
    r'Подарок при заказе 🎁', r'🚚 Доставка 🎁 Подарок 💰 Скидка',
    r'Узнать цену', r'❗️', r'💲', r'🏷️', r'звоните', r'8', r'\+',
    r'7', r'₽', r'закажите'
]

# Разрешенные домены
ALLOWED_DOMAINS = [
    'github.com', 'wikipedia.org', 'google.com',
    'youtube.com', 'stackoverflow.com'
]

# Настройки
WARN_LIMIT = 3
DELETE_MESSAGES = True
TEMP_BAN_DURATION = 3600  # 1 час

# ====================== ДЕТЕКТОР РЕКЛАМЫ ======================
class AdDetector:
    def __init__(self):
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.UNICODE) 
                                 for pattern in AD_KEYWORDS]
    
    def is_advertisement(self, text: str) -> bool:
        """Проверка текста на рекламу"""
        if not text or not isinstance(text, str):
            return False
        
        text = text.strip()
        
        # Проверка по паттернам
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                # Проверяем, не является ли ссылка разрешенной
                if self._is_allowed_url(text):
                    continue
                return True
        
        # Проверка на CAPS LOCK
        if self._check_caps_lock(text):
            return True
        
        # Проверка на спам (много повторяющихся символов)
        if self._check_spam_patterns(text):
            return True
        
        return False
    
    def _is_allowed_url(self, text: str) -> bool:
        """Проверка разрешенных доменов"""
        urls = re.findall(r'https?://[^\s]+', text.lower())
        for url in urls:
            if any(domain in url for domain in ALLOWED_DOMAINS):
                return True
        return False
    
    def _check_caps_lock(self, text: str) -> bool:
        """Проверка на CAPS LOCK"""
        if len(text) < 15:
            return False
        
        letters = [c for c in text if c.isalpha()]
        if len(letters) < 10:
            return False
        
        upper_count = sum(1 for c in letters if c.isupper())
        return upper_count / len(letters) > 0.6
    
    def _check_spam_patterns(self, text: str) -> bool:
        """Проверка спам-паттернов"""
        # Много повторяющихся символов подряд
        if re.search(r'(.)\1{5,}', text):
            return True
        
        # Много восклицательных или вопросительных знаков
        if text.count('!') > 5 or text.count('?') > 5:
            return True
        
        return False

# ====================== ИНИЦИАЛИЗАЦИЯ ======================
detector = AdDetector()
user_warnings = defaultdict(int)  # Хранение предупреждений

# ====================== ОБРАБОТЧИКИ КОМАНД ======================
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
        
        user_warnings[user_id] += 1
        warnings = user_warnings[user_id]
        
        if warnings >= WARN_LIMIT:
            try:
                bot.ban_chat_member(message.chat.id, user_id, until_date=int(time.time()) + TEMP_BAN_DURATION)
                bot.reply_to(message, f"🚷 @{username} был забанен за {WARN_LIMIT} предупреждения!")
                user_warnings.pop(user_id)  # Удаляем из статистики
            except Exception as e:
                bot.reply_to(message, f"❌ Не удалось забанить пользователя: {e}")
        else:
            bot.reply_to(message, f"⚠️ @{username}, вам выдано предупреждение! Всего: {warnings}/{WARN_LIMIT}")

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
    cleared_count = len(user_warnings)
    user_warnings.clear()
    
    if cleared_count > 0:
        bot.reply_to(message, f"✅ Все предупреждения сняты! Очищено: {cleared_count} записей.")
    else:
        bot.reply_to(message, "ℹ️ Нет активных предупреждений для очистки.")

@bot.message_handler(commands=['reset_warns'])
def reset_warns(message):
    """Сбросить предупреждения конкретному пользователю"""
    if message.chat.type == "private":
        bot.reply_to(message, "❌ Эта команда работает только в группах!")
        return
    
    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ['administrator', 'creator']:
            bot.reply_to(message, "❌ Только администраторы могут использовать эту команду!")
            return
    except:
        bot.reply_to(message, "❌ Ошибка проверки прав!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение пользователя!")
        return
    
    user_id = message.reply_to_message.from_user.id
    username = message.reply_to_message.from_user.username or message.reply_to_message.from_user.first_name
    
    if user_id in user_warnings:
        user_warnings.pop(user_id)
        bot.reply_to(message, f"✅ Предупреждения пользователя @{username} сброшены!")
    else:
        bot.reply_to(message, f"ℹ️ У пользователя @{username} нет предупреждений.")

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
📋 Доступные команды:
/start - Запустить бота
/help - Показать это сообщение
/stats - Показать статистику предупреждений (только в группах)
/warn - Выдать предупреждение пользователю (ответьте на сообщение)
/unwarn - Снять все предупреждения (только админы)
/reset_warns - Сбросить предупреждения пользователю (админы, ответьте на сообщение)

🔒 Бот автоматически блокирует:
• Рекламные сообщения и спам
• Ссылки (кроме разрешенных)
• Сообщения в CAPS LOCK
• Финансовые мошенничества
"""
    bot.reply_to(message, help_text)

# ====================== ОБРАБОТКА СООБЩЕНИЙ ======================
@bot.message_handler(content_types=['text', 'photo', 'voice'])
def check_ad(message):
    # Получаем текст сообщения
    text = ""
    if message.content_type == 'text':
        text = message.text
    elif message.content_type == 'photo' and message.caption:
        text = message.caption
    elif message.content_type == 'voice':
        bot.send_message(message.chat.id, "☢️Включите блокировку голосовых сообщений...☢️")
        return
    
    # Проверяем на рекламу с использованием AdDetector
    if text and detector.is_advertisement(text):
        try:
            # Удаляем сообщение
            if DELETE_MESSAGES:
                bot.delete_message(message.chat.id, message.message_id)
            
            # Отправляем предупреждение
            if message.chat.type == "private":
                warn_text = "❌ Реклама запрещена в личных сообщениях!"
                bot.send_message(message.chat.id, warn_text)
            else:
                user_id = message.from_user.id
                username = message.from_user.username or message.from_user.first_name
                
                # Увеличиваем счетчик предупреждений
                user_warnings[user_id] += 1
                warnings = user_warnings[user_id]
                
                # Формируем текст предупреждения
                if warnings == 1:
                    warn_text = f"⚠️ @{username}, реклама запрещена! Первое предупреждение. (1/{WARN_LIMIT})"
                elif warnings == 2:
                    warn_text = f"⚠️ @{username}, реклама запрещена! Второе предупреждение. (2/{WARN_LIMIT})"
                elif warnings >= WARN_LIMIT:
                    try:
                        # Блокируем пользователя
                        bot.ban_chat_member(
                            message.chat.id, 
                            user_id, 
                            until_date=int(time.time()) + TEMP_BAN_DURATION
                        )
                        warn_text = f"🚷 @{username} был забанен за {WARN_LIMIT} предупреждения!"
                        # Удаляем из статистики
                        user_warnings.pop(user_id, None)
                    except Exception as e:
                        warn_text = f"❌ Не удалось забанить @{username}. Ошибка: {e}"
                
                # Отправляем предупреждение
                sent_msg = bot.send_message(message.chat.id, warn_text)
                
                # Удаляем предупреждение через 10 секунд (опционально)
                # Можно раскомментировать, если нужно:
                # import threading
                # def delete_later():
                #     time.sleep(10)
                #     try:
                #         bot.delete_message(message.chat.id, sent_msg.message_id)
                #     except:
                #         pass
                # threading.Thread(target=delete_later).start()
                
        except Exception as e:
            print(f"Ошибка при обработке сообщения: {e}")

# ====================== ЗАПУСК БОТА ======================
if __name__ == "__main__":
    print("🚀 Бот-блокировщик рекламы запущен!")
    print("📱 Используйте команды /start и /help для начала работы")
    print(f"🔍 Загружено {len(AD_KEYWORDS)} паттернов для блокировки рекламы")
    
    try:
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

