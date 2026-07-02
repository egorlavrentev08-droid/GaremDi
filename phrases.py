# phrases.py

import json
import os
import random
import logging
from typing import Dict, List, Optional

from config import TRIGGER_SYMBOLS, MOOD_SYMBOLS, is_admin

logger = logging.getLogger(__name__)

PHRASES_FILE = "phrases.json"

# Кеш в памяти
phrase_cache = {}

# ============================================================
# 1. ЗАГРУЗКА И СОХРАНЕНИЕ
# ============================================================

def load_phrases() -> Dict:
    """Загружает фразы из JSON-файла в кеш"""
    global phrase_cache
    
    if not os.path.exists(PHRASES_FILE):
        with open(PHRASES_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        phrase_cache = {}
        return {}
    
    try:
        with open(PHRASES_FILE, 'r', encoding='utf-8') as f:
            phrase_cache = json.load(f)
            logger.info(f"📚 Загружено фраз: {sum(len(v) for v in phrase_cache.values())}")
            return phrase_cache
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки фраз: {e}")
        phrase_cache = {}
        return {}

def save_phrases() -> bool:
    """Сохраняет кеш в JSON-файл"""
    try:
        with open(PHRASES_FILE, 'w', encoding='utf-8') as f:
            json.dump(phrase_cache, f, ensure_ascii=False, indent=2)
        logger.info("💾 Фразы сохранены")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения фраз: {e}")
        return False

# ============================================================
# 2. ПАРСЕР СООБЩЕНИЙ (ТВОЯ СИСТЕМА СИМВОЛОВ)
# ============================================================

def parse_phrase(text: str) -> dict | None:
    """
    Парсит сообщение формата: !₽ Текст фразы
    Возвращает: {trigger, mood, text} или None
    """
    if len(text) < 2:
        return None
    
    trigger_symbol = text[0]
    mood_symbol = text[1]
    
    if trigger_symbol not in TRIGGER_SYMBOLS:
        return None
    if mood_symbol not in MOOD_SYMBOLS:
        return None
    
    phrase_text = text[2:].strip()
    if len(phrase_text) < 7:
        return None
    
    return {
        'trigger': TRIGGER_SYMBOLS[trigger_symbol],
        'mood': MOOD_SYMBOLS[mood_symbol],
        'text': phrase_text
    }

# ============================================================
# 3. ДОБАВЛЕНИЕ ФРАЗЫ
# ============================================================

def add_phrase_from_text(text: str) -> tuple[bool, str, dict | None]:
    """Добавляет фразу из строки с символами"""
    parsed = parse_phrase(text)
    if not parsed:
        return False, "❌ Неверный формат! Используй: !₽ Текст", None
    
    trigger = parsed['trigger']
    mood = parsed['mood']
    phrase_text = parsed['text']
    
    if trigger not in phrase_cache:
        phrase_cache[trigger] = []
    
    # Проверка дубликата
    for p in phrase_cache[trigger]:
        if p['text'].lower() == phrase_text.lower():
            return False, "⚠️ Такая фраза уже есть!", None
    
    return True, "✅ Фраза готова к добавлению", parsed

def confirm_add_phrase(trigger: str, mood: str, text: str) -> bool:
    """Подтверждает добавление фразы после кнопки"""
    if trigger not in phrase_cache:
        phrase_cache[trigger] = []
    
    phrase_cache[trigger].append({
        'text': text,
        'mood': mood
    })
    
    save_phrases()
    return True

# ============================================================
# 4. УДАЛЕНИЕ ФРАЗЫ
# ============================================================

def delete_phrase_by_global_index(index: int) -> tuple[bool, str]:
    """Удаляет фразу по глобальному номеру (1-based)"""
    all_phrases = get_all_phrases()
    
    if index < 1 or index > len(all_phrases):
        return False, f"❌ Фраза #{index} не найдена"
    
    phrase = all_phrases[index - 1]
    trigger = phrase['trigger']
    text = phrase['text']
    
    # Находим и удаляем в кеше
    if trigger in phrase_cache:
        for i, p in enumerate(phrase_cache[trigger]):
            if p['text'] == text:
                del phrase_cache[trigger][i]
                save_phrases()
                return True, f"✅ Фраза #{index} удалена: {text[:30]}..."
    
    return False, "❌ Ошибка при удалении"

# ============================================================
# 5. ПОЛУЧЕНИЕ СПИСКОВ ФРАЗ
# ============================================================

def get_all_phrases() -> List[dict]:
    """Возвращает все фразы с глобальными индексами"""
    result = []
    for trigger, phrases in phrase_cache.items():
        for p in phrases:
            result.append({
                'trigger': trigger,
                'mood': p['mood'],
                'text': p['text'],
                'index': len(result) + 1
            })
    return result

def get_filtered_phrases(trigger: str = None, mood: str = None) -> List[dict]:
    """Возвращает отфильтрованные фразы с глобальными индексами"""
    all_phrases = get_all_phrases()
    
    filtered = all_phrases
    if trigger:
        filtered = [p for p in filtered if p['trigger'] == trigger]
    if mood:
        filtered = [p for p in filtered if p['mood'] == mood]
    
    return filtered

# ============================================================
# 6. ПОЛУЧЕНИЕ СЛУЧАЙНЫХ ФРАЗ (ДЛЯ CORE)
# ============================================================

def get_random_phrase(trigger: str, mood: str = None) -> Optional[str]:
    """Возвращает случайную фразу для триггера"""
    phrases = phrase_cache.get(trigger, [])
    if not phrases:
        return None
    if mood:
        filtered = [p for p in phrases if p['mood'] == mood]
        if filtered:
            return random.choice(filtered)['text']
    return random.choice(phrases)['text']

def get_rank_phrase(rank_name: str) -> Optional[str]:
    """Возвращает фразу для ранга"""
    phrases = phrase_cache.get('RANK', [])
    rank_phrases = [p for p in phrases if rank_name.lower() in p['text'].lower()]
    if not rank_phrases:
        return None
    return random.choice(rank_phrases)['text']

def get_streak_achievement(day: int) -> Optional[str]:
    """Возвращает фразу для достижения стрика"""
    phrases = phrase_cache.get('STREAK_ACHIEVEMENT', [])
    day_phrases = [p for p in phrases if str(day) in p['text']]
    if not day_phrases:
        return None
    return random.choice(day_phrases)['text']

# ============================================================
# 7. СТАТИСТИКА
# ============================================================

def get_stats() -> Dict:
    """Возвращает статистику по триггерам"""
    return {
        trigger: len(phrases)
        for trigger, phrases in phrase_cache.items()
    }

# ============================================================
# 8. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ФИЛЬТРОВ
# ============================================================

def get_trigger_from_alias(alias: str) -> str | None:
    """Преобразует название в триггер"""
    alias = alias.lower()
    for key, value in TRIGGER_SYMBOLS.items():
        if value.lower() == alias:
            return value
    return None

def get_mood_from_alias(alias: str) -> str | None:
    """Преобразует название в настроение"""
    alias = alias.lower()
    for key, value in MOOD_SYMBOLS.items():
        if value.lower() == alias:
            return value
    return None
