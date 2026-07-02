# ID основного чата
CHAT_ID = -1002497100583

# ID чата админов (новый!)
ADMIN_CHAT_ID = -1003882801763

# Ссылки (опционально)
CHAT_LINK = "@Gar3mDi"
ADMIN_CHAT_LINK = "@админ_чат_ссылка"  # если нужно

# ID администраторов
ADMIN_IDS = [
    6595788533,  # Твой ID
    1903870420,
    7975256831 # Второй админ (если есть)
]

# Путь к базе данных
DB_PATH = "dori.db"

# ============================================================
# СИМВОЛЫ ДЛЯ ФРАЗ (ТВОЯ СИСТЕМА!)
# ============================================================

# Триггеры
TRIGGER_SYMBOLS = {
    '!': '1_DAY_INACTIVE',
    '?': '2_PLUS_DAYS_INACTIVE',
    '~': 'ACTIVITY_RESUMED_AFTER_BREAK',
    '∆': 'RANK',
    '%': 'STREAK_ACHIEVEMENT'
}

# Настроения
MOOD_SYMBOLS = {
    '₽': 'ANXIOUS',
    '£': 'ANGRY',
    '€': 'SARCASTIC',
    '$': 'MOTIVATIONAL',
    '¢': 'FRIENDLY'
}

# ============================================================
# НАЗВАНИЯ И ЭМОДЗИ
# ============================================================

TRIGGER_NAMES = {
    '1_DAY_INACTIVE': 'день',
    '2_PLUS_DAYS_INACTIVE': 'несколько',
    'ACTIVITY_RESUMED_AFTER_BREAK': 'возвращение',
    'RANK': 'ранг',
    'STREAK_ACHIEVEMENT': 'призыв'
}

MOOD_NAMES = {
    'ANXIOUS': 'тревожное',
    'ANGRY': 'злое',
    'SARCASTIC': 'саркастичное',
    'MOTIVATIONAL': 'мотивирующее',
    'FRIENDLY': 'дружелюбное'
}

TRIGGER_EMOJI = {
    '1_DAY_INACTIVE': '❗',
    '2_PLUS_DAYS_INACTIVE': '❓',
    'ACTIVITY_RESUMED_AFTER_BREAK': '🔄',
    'RANK': '🏆',
    'STREAK_ACHIEVEMENT': '⭐'
}

MOOD_EMOJI = {
    'ANXIOUS': '😰',
    'ANGRY': '😡',
    'SARCASTIC': '😏',
    'MOTIVATIONAL': '💪',
    'FRIENDLY': '🤗'
}

# ============================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def is_allowed_chat(chat_id: int) -> bool:
    """Проверяет, разрешён ли чат для работы бота"""
    return chat_id in [CHAT_ID, ADMIN_CHAT_ID]

# config.py

# ... (остальной код)

async def is_admin_in_chat(user_id: int, bot: Bot) -> bool:
    """Проверяет, состоит ли пользователь в админском чате"""
    try:
        chat_member = await bot.get_chat_member(ADMIN_CHAT_ID, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except:
        return False
