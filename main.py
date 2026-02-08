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
    # Основные рекламные слова
    r'купить', r'продам', r'продажа', r'скидк[а-я]*', r'распродаж',
    r'заказ[а-я]*', r'доставк[а-я]*', r'магазин', r'интернет[-\s]*магазин',
    r'бесплатно', r'акци[я-я]*', r'только сегодня', r'выгодно',
    r'реклам[а-я]*', r'объявлени[е-я]*', r'предложени[е-я]*',
    r'спешите', r'ограниченно', r'последни[е-я]*',
    
    # Финансовые мошенничества
    r'кредит[а-я]*', r'займ[а-я]*', r'быстр[а-я]* деньг[а-я]*',
    r'инвестиц[а-я]*', r'крипто', r'bitcoin', r'брокер',
    r'заработ[а-я]*', r'удаленн[а-я]* работ[а-я]*',
    r'дoxoд', r'заработок', r'зарплат[а-я]*', r'прибыль',  # Для "Пoлyчи дoxod"
    r'гарант[а-я]*', r'100%',  # Для "100% gаrаnт"
    
    # Ссылки и домены
    r'http[s]?://', r'www\.', r't\.me/', r'@[A-Za-z0-9_]{5,}',
    r'(?:https?://)?(?:t\.me/|telegram\.me/)',
    r'\.online', r'\.site', r'\.xyz', r'\.club', r'\.top',  # Подозрительные домены
    r'tgram', r'telegram', r'подтвердит[е-я]* вход',  # Для фейковых сообщений
    
    # Мошеннические фразы
    r'ваш аккаунт', r'будет удал[её]н', r'через.*час[а-я]*',
    r'подтвердит[е-я]*', r'вход', r'авторизац[и-я]*',
    r'в личк[уе]', r'в лс', r'пиши в лс', r'напиши в лс',
    r'без вложени[ийй]', r'без инвестиц[и-я]*',
    
    # Эмодзи и символы
    r'💵{2,}', r'💸{2,}', r'💰{2,}',  # Много денежных эмодзи
    r'\$+\s*[0-9]+', r'₽+\s*[0-9]+',  # Деньги с цифрами
    
    # Капс
    r'^[^a-zа-яё]{10,}$',  # Сообщения без строчных букв
    
    # Дополнительные слова из второго кода
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

# ====================== АНТИФЛУД СИСТЕМА ======================
last_message_time = {}  # {user_id: timestamp}

# ====================== ДЕТЕКТОР РЕКЛАМЫ И МОШЕННИЧЕСТВА ======================
class AdDetector:
    def __init__(self):
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.UNICODE) 
                                 for pattern in AD_KEYWORDS]
        
        # Специальные паттерны для хитрых сообщений
        self.special_patterns = [
            # Паттерн для "З а р а б о т о к" (пробелы между буквами)
            re.compile(r'[а-яё]\s+[а-яё]\s+[а-яё]\s+[а-яё]\s+[а-яё]\s+[а-яё]\s+[а-яё]', re.IGNORECASE),
            
            # Паттерн для "Пoлyчи дoxod" (латинские буквы вместо кириллицы)
            re.compile(r'[a-z][а-яё]|[а-яё][a-z]', re.IGNORECASE),  # Смешанные буквы
            
            # Паттерн для "100% gаrаnт" (смешанные алфавиты)
            re.compile(r'\d+%\s*[a-zа-яё]+', re.IGNORECASE),
            
            # Паттерн для фейковых угроз удаления аккаунта
            re.compile(r'аккаунт.*удал[её]н.*\d+\s*(час|день|сутк)', re.IGNORECASE),
            
            # Паттерн для "в лс" / "в личку"
            re.compile(r'в\s*(лс|личк[уе]|п[рл]ям[ыи]е)', re.IGNORECASE),
        ]
    
    def is_advertisement(self, text: str) -> bool:
        """Проверка текста на рекламу/мошенничество"""
        if not text or not isinstance(text, str):
            return False
        
        text = text.strip()
        
        # 1. Проверка на очевидную рекламу по паттернам
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                # Проверяем, не является ли ссылка разрешенной
                if self._is_allowed_url(text):
                    continue
                return True
        
        # 2. Проверка специальных паттернов (хитрые сообщения)
        for pattern in self.special_patterns:
            if pattern.search(text):
                return True
        
        # 3. Проверка на хитрости с пробелами (пример: "З а р а б о т о к")
        if self._check_spaced_text(text):
            return True
        
        # 4. Проверка на смешанные алфавиты (пример: "Пoлyчи дoxod")
        if self._check_mixed_alphabet(text):
            return True
        
        # 5. Проверка на CAPS LOCK
        if self._check_caps_lock(text):
            return True
        
        # 6. Проверка на спам (много повторяющихся символов)
        if self._check_spam_patterns(text):
            return True
        
        # 7. Проверка на подозрительные комбинации эмодзи и текста
        if self._check_suspicious_emoji_patterns(text):
            return True
        
        return False
    
    def _check_spaced_text(self, text: str) -> bool:
        """Проверка на текст с пробелами между буквами"""
        # Пример: "З а р а б о т о к" или "б е з в л о ж е н и й"
        
        # Ищем слова, где буквы разделены пробелами
        words = text.split()
        
        # Проверяем длинные последовательности коротких "слов" (1-2 символа)
        suspicious_sequence = 0
        for word in words:
            if 1 <= len(word) <= 2 and word.isalpha():
                suspicious_sequence += 1
                if suspicious_sequence >= 5:  # 5+ коротких слов подряд
                    return True
            else:
                suspicious_sequence = 0
        
        return False
    
    def _check_mixed_alphabet(self, text: str) -> bool:
        """Проверка на смешанные кириллицу и латиницу (хитрость мошенников)"""
        # Пример: "Пoлyчи дoxod" (где 'o' и 'x' латинские, остальное кириллица)
        
        # Убираем эмодзи и символы, оставляем только буквы
        letters = [c for c in text if c.isalpha()]
        if len(letters) < 10:
            return False
        
        # Считаем кириллические и латинские буквы
        cyrillic_count = sum(1 for c in letters if '\u0400' <= c <= '\u04FF')
        latin_count = len(letters) - cyrillic_count
        
        # Если есть и те, и другие в заметном количестве
        if cyrillic_count >= 5 and latin_count >= 2:
            # Проверяем, не обычное ли это английское слово в русском тексте
            words = text.lower().split()
            common_english = ['ok', 'hi', 'hello', 'yes', 'no', 'web', 'net', 'com']
            english_words_count = sum(1 for word in words if word in common_english)
            
            # Если много латинских букв и мало обычных английских слов
            if latin_count > english_words_count * 3:
                return True
        
        return False
    
    def _check_suspicious_emoji_patterns(self, text: str) -> bool:
        """Проверка на подозрительные комбинации эмодзи и текста"""
        # Пример: "💵💵💵" + текст про заработок
        
        # Считаем денежные эмодзи
        money_emojis = ['💵', '💸', '💰', '💲', '💶', '💷', '🤑', '💳']
        money_count = sum(text.count(emoji) for emoji in money_emojis)
        
        # Если много денежных эмодзи
        if money_count >= 3:
            # Проверяем, есть ли рядом слова про деньги/заработок
            money_words = ['деньги', 'зарплат', 'доход', 'заработ', 'прибыль', 
                          'плат', 'оплат', 'выплат', 'перевод', 'наличн']
            text_lower = text.lower()
            
            if any(word in text_lower for word in money_words):
                return True
        
        # Проверка на эмодзи в начале + текст мошенничества
        if len(text) > 0:
            first_char = text[0]
            if first_char in money_emojis:
                # Проверяем первые 50 символов на слова мошенничества
                first_part = text[:50].lower()
                scam_words = ['аккаунт', 'удал', 'подтверд', 'вход', 'авториз', 
                             'получ', 'гарант', '100%', 'без влож']
                
                if any(word in first_part for word in scam_words):
                    return True
        
        return False
    
    def _is_allowed_url(self, text: str) -> bool:
        """Проверка разрешенных доменов"""
        urls = re.findall(r'https?://[^\s]+', text.lower())
        for url in urls:
            if any(domain in url for domain in ALLOWED_DOMAINS):
                return True
            
            # Проверяем на подозрительные домены
            suspicious_domains = ['.online', '.site', '.xyz', '.club', '.top', 
                                 'tgram-auth', 'telegram-verify']
            if any(domain in url for domain in suspicious_domains):
                return False  # Блокируем подозрительные
        
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
        
        # Много эмодзи подряд
        emoji_pattern = re.compile(
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0]{3,}'
        )
        if emoji_pattern.search(text):
            # Проверяем, не обычные ли это эмоции
            positive_emojis = ['😀', '😂', '🥰', '😊', '👍', '❤️', '🎉', '🤗']
            emoji_count = sum(text.count(emoji) for emoji in positive_emojis)
            if emoji_count < 3:  # Если мало позитивных эмодзи
                return True
        
        return False

# ====================== ИНИЦИАЛИЗАЦИЯ ======================
detector = AdDetector()
user_warnings = defaultdict(int)  # Хранение предупреждений

# ====================== ОБРАБОТЧИКИ КОМАНД ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚫 Антиреклама активна! Сообщения с рекламой и мошенничеством удаляются. Помощь /help")

@bot.message_handler(commands=['test'])
def test_detector(message):
    """Тестовая команда для проверки детектора"""
    if message.chat.type == "private":
        test_cases = [
            "💵💵💵\nПoлyчи дoxod yжe ceгoдня\n100% gаrаnт",
            "З а р а б о т о к 💸\nб е з   в л о ж е н и й\nп и ш и  в  л с",
            "Ваш аккаунт Telegram будет удалён через 24 часа\nПодтвердите вход: tgram-auth.online",
            "Привет, как дела? Это обычное сообщение.",
            "Скидка 50% на все товары!",
            "💰💰💰 ЗАРАБОТОК БЕЗ ВЛОЖЕНИЙ 💰💰💰"
        ]
        
        for test_text in test_cases:
            result = detector.is_advertisement(test_text)
            status = "🔴 СПАМ" if result else "🟢 НОРМА"
            bot.reply_to(message, f"{status}:\n{test_text[:100]}...")

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
/test - Тест детектора (в личке)

🔒 Бот автоматически блокирует:
• Обычную рекламу и спам
• Финансовые мошенничества ("заработок без вложений")
• Фейковые угрозы ("аккаунт будет удален")
• Хитрые сообщения с пробелами между буквами
• Сообщения со смешанными алфавитами (латиница+кириллица)
• Подозрительные ссылки (.online, .xyz и т.д.)
• Сообщения в CAPS LOCK
• Флуд (сообщения чаще чем раз в 3 секунды)
"""
    bot.reply_to(message, help_text)

# ====================== ОБРАБОТКА ВСЕХ СООБЩЕНИЙ (АНТИФЛУД) ======================
@bot.message_handler(func=lambda m: True)
def all_messages(message):
    """Обработка всех сообщений с антифлудом"""
    
    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        return
    
    # Антифлуд: проверяем время между сообщениями
    uid = message.from_user.id
    now = time.time()
    
    if uid in last_message_time and now - last_message_time[uid] < 3:
        try:
            bot.send_message(message.chat.id, "⏳ Подождите 3 секунды между сообщениями")
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        return
    
    last_message_time[uid] = now
    
    # Дальше проверяем на рекламу
    check_ad(message)

# ====================== ПРОВЕРКА НА РЕКЛАМУ ======================
def check_ad(message):
    """Проверка сообщения на рекламу"""
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
                warn_text = "❌ Реклама и мошенничество запрещены в личных сообщениях!"
                bot.send_message(message.chat.id, warn_text)
            else:
                user_id = message.from_user.id
                username = message.from_user.username or message.from_user.first_name
                
                # Увеличиваем счетчик предупреждений
                user_warnings[user_id] += 1
                warnings = user_warnings[user_id]
                
                # Определяем тип нарушения для более точного сообщения
                violation_type = "мошенничество" if detector._check_mixed_alphabet(text) or "аккаунт" in text.lower() else "реклама"
                
                # Формируем текст предупреждения
                if warnings == 1:
                    warn_text = f"⚠️ @{username}, {violation_type} запрещена! Первое предупреждение. (1/{WARN_LIMIT})"
                elif warnings == 2:
                    warn_text = f"⚠️ @{username}, {violation_type} запрещена! Второе предупреждение. (2/{WARN_LIMIT})"
                elif warnings >= WARN_LIMIT:
                    try:
                        # Блокируем пользователя
                        bot.ban_chat_member(
                            message.chat.id, 
                            user_id, 
                            until_date=int(time.time()) + TEMP_BAN_DURATION
                        )
                        warn_text = f"🚷 @{username} был забанен за {violation_type} ({WARN_LIMIT} предупреждения)!"
                        # Удаляем из статистики
                        user_warnings.pop(user_id, None)
                    except Exception as e:
                        warn_text = f"❌ Не удалось забанить @{username}. Ошибка: {e}"
                
                # Отправляем предупреждение
                sent_msg = bot.send_message(message.chat.id, warn_text)
                
                # Удаляем предупреждение через 10 секунд
                def delete_warning():
                    time.sleep(10)
                    try:
                        bot.delete_message(message.chat.id, sent_msg.message_id)
                    except:
                        pass
                
                import threading
                threading.Thread(target=delete_warning).start()
                
        except Exception as e:
            print(f"Ошибка при обработке сообщения: {e}")

# ====================== ЗАПУСК БОТА ======================
if __name__ == "__main__":
    print("🚀 Бот-блокировщик рекламы и мошенничества запущен!")
    print("📱 Используйте команды /start и /help для начала работы")
    print(f"🔍 Загружено {len(AD_KEYWORDS)} паттернов для блокировки")
    print("⏳ Антифлуд система активна (3 секунды между сообщениями)")
    print("🛡️  Детектор обучен распознавать хитрые сообщения мошенников")
    
    try:
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

