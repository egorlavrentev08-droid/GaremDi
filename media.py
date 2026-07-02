# media.py

import os
import random
import asyncio
import logging
from typing import List, Optional, Dict

from config import TRIGGER_SYMBOLS, MOOD_SYMBOLS

logger = logging.getLogger(__name__)

# ============================================================
# 1. СОКРАЩЕНИЯ ДЛЯ ПАПОК
# ============================================================

TRIGGER_CODE = {
    '1_DAY_INACTIVE': 'ina',
    '2_PLUS_DAYS_INACTIVE': 'plu',
    'ACTIVITY_RESUMED_AFTER_BREAK': 'ret',
    'RANK': 'ran',
    'STREAK_ACHIEVEMENT': 'str'
}

MOOD_CODE = {
    'ANXIOUS': 'anx',
    'ANGRY': 'ang',
    'SARCASTIC': 'sar',
    'MOTIVATIONAL': 'mot',
    'FRIENDLY': 'fri'
}

BASE_PATH = "content"

# ============================================================
# 2. СОЗДАНИЕ ПАПОК (ДЛЯ MAIN.PY ПРИ ПЕРВОМ ЗАПУСКЕ)
# ============================================================

def create_media_folders():
    """Создаёт 53 папки для картинок и мемов при первом запуске"""
    
    print("🛠️ Создаю структуру папок для картинок...")
    
    # 1. Корень
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)
        print(f"📁 Создана папка: {BASE_PATH}")
    
    # 2. pics и mems
    for folder in [f"{BASE_PATH}/pics", f"{BASE_PATH}/mems"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"📁 Создана папка: {folder}")
    
    # 3. Создаём папки для pics (триггер_настроение)
    for trigger_code in TRIGGER_CODE.values():
        for mood_code in MOOD_CODE.values():
            folder = f"{BASE_PATH}/pics/{trigger_code}_{mood_code}"
            if not os.path.exists(folder):
                os.makedirs(folder)
                print(f"📁 Создана папка: {folder}")
    
    # 4. Создаём папки для mems (триггер_настроение_mem)
    for trigger_code in TRIGGER_CODE.values():
        for mood_code in MOOD_CODE.values():
            folder = f"{BASE_PATH}/mems/{trigger_code}_{mood_code}_mem"
            if not os.path.exists(folder):
                os.makedirs(folder)
                print(f"📁 Создана папка: {folder}")
    
    print("✅ Все 53 папки для картинок и мемов созданы!")

# ============================================================
# 3. ПОЛУЧЕНИЕ СПИСКА ФАЙЛОВ В ПАПКЕ (СИНХРОННАЯ)
# ============================================================

def _get_files_in_folder_sync(folder_path: str) -> List[str]:
    """Синхронная функция для получения списка файлов"""
    if not os.path.exists(folder_path):
        return []
    
    files = []
    for f in os.listdir(folder_path):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            files.append(os.path.join(folder_path, f))
    
    return files

# ============================================================
# 4. ПОЛУЧЕНИЕ СЛУЧАЙНОЙ КАРТИНКИ (АСИНХРОННАЯ!)
# ============================================================

async def get_random_picture(trigger: str, mood: str = None, is_meme: bool = False) -> Optional[str]:
    """
    Асинхронно возвращает путь к случайной картинке.
    Ищет в папках trigger_mood или trigger_mood_mem.
    Если mood = None — берёт любую из папок с этим триггером.
    """
    # Синхронную работу выносим в отдельный поток, чтобы не блокировать event loop
    return await asyncio.to_thread(_get_random_picture_sync, trigger, mood, is_meme)

def _get_random_picture_sync(trigger: str, mood: str = None, is_meme: bool = False) -> Optional[str]:
    """Синхронная версия для вызова в отдельном потоке"""
    trigger_code = TRIGGER_CODE.get(trigger)
    if not trigger_code:
        return None
    
    folder_type = 'mems' if is_meme else 'pics'
    suffix = '_mem' if is_meme else ''
    
    # Если настроение указано — ищем только в конкретной папке
    if mood:
        mood_code = MOOD_CODE.get(mood)
        if not mood_code:
            return None
        
        folder = f"{BASE_PATH}/{folder_type}/{trigger_code}_{mood_code}{suffix}"
        files = _get_files_in_folder_sync(folder)
        if files:
            return random.choice(files)
        return None
    
    # Если настроение не указано — ищем в любой папке с этим триггером
    base = f"{BASE_PATH}/{folder_type}"
    if not os.path.exists(base):
        return None
    
    all_files = []
    for folder in os.listdir(base):
        if folder.startswith(f"{trigger_code}_") and folder.endswith(suffix):
            folder_path = os.path.join(base, folder)
            all_files.extend(_get_files_in_folder_sync(folder_path))
    
    if all_files:
        return random.choice(all_files)
    return None

# ============================================================
# 5. СТАТИСТИКА ПО КАРТИНКАМ (ДЛЯ ADMIN)
# ============================================================

def get_media_stats() -> Dict:
    """Возвращает статистику по всем папкам"""
    stats = {
        'pics': {},
        'mems': {}
    }
    
    for folder_type in ['pics', 'mems']:
        base = f"{BASE_PATH}/{folder_type}"
        if not os.path.exists(base):
            continue
        
        for folder in os.listdir(base):
            folder_path = os.path.join(base, folder)
            if os.path.isdir(folder_path):
                count = len(_get_files_in_folder_sync(folder_path))
                if count > 0:
                    stats[folder_type][folder] = count
    
    return stats

# ============================================================
# 6. ПОЛУЧЕНИЕ КАРТИНОК ДЛЯ ПРОСМОТРА (ДЛЯ ADMIN)
# ============================================================

def get_pictures_for_view(trigger: str = None, mood: str = None, is_meme: bool = False) -> List[str]:
    """
    Возвращает список картинок для просмотра с фильтрацией.
    Фильтры: trigger, mood, is_meme
    """
    all_files = []
    folder_type = 'mems' if is_meme else 'pics'
    base = f"{BASE_PATH}/{folder_type}"
    
    if not os.path.exists(base):
        return []
    
    # Если фильтры не указаны — берём всё
    if not trigger and not mood:
        for folder in os.listdir(base):
            folder_path = os.path.join(base, folder)
            if os.path.isdir(folder_path):
                all_files.extend(_get_files_in_folder_sync(folder_path))
        return all_files
    
    # С фильтрами
    trigger_code = TRIGGER_CODE.get(trigger) if trigger else None
    mood_code = MOOD_CODE.get(mood) if mood else None
    suffix = '_mem' if is_meme else ''
    
    for folder in os.listdir(base):
        folder_path = os.path.join(base, folder)
        if not os.path.isdir(folder_path) or not folder.endswith(suffix):
            continue
        
        # Проверяем, подходит ли папка под фильтры
        if trigger_code and mood_code:
            if folder == f"{trigger_code}_{mood_code}{suffix}":
                all_files.extend(_get_files_in_folder_sync(folder_path))
        elif trigger_code:
            if folder.startswith(f"{trigger_code}_"):
                all_files.extend(_get_files_in_folder_sync(folder_path))
        elif mood_code:
            if folder.endswith(f"_{mood_code}{suffix}"):
                all_files.extend(_get_files_in_folder_sync(folder_path))
    
    return all_files

# ============================================================
# 7. ПОЛУЧЕНИЕ ПУТИ К ПАПКЕ ПО ФИЛЬТРАМ (ДЛЯ СОХРАНЕНИЯ)
# ============================================================

def get_folder_path(trigger: str, mood: str, is_meme: bool = False) -> str:
    """Возвращает путь к папке для сохранения картинки"""
    trigger_code = TRIGGER_CODE.get(trigger, 'all')
    mood_code = MOOD_CODE.get(mood, 'all')
    folder_type = 'mems' if is_meme else 'pics'
    suffix = '_mem' if is_meme else ''
    
    return f"{BASE_PATH}/{folder_type}/{trigger_code}_{mood_code}{suffix}"
