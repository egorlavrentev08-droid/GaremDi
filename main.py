# main.py

import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import BotCommand, Message
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import initialize_database
from config import ADMIN_IDS, is_admin, CHAT_ID

from core import (
    register_handlers,
    chat_filter,
    check_inactive_users,
    daily_reset_and_reward,
    weekly_streak_reward,
    check_expired_redemptions_task,
    set_phrase_functions
)
from admin import register_admin_handlers
from phrases import load_phrases, get_random_phrase, get_rank_phrase, get_streak_achievement
from media import create_media_folders

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация планировщика
scheduler = AsyncIOScheduler()


# ============================================================
# ЗАПУСК И ОСТАНОВКА
# ============================================================

async def on_startup(bot: Bot):
    """Действия при старте бота"""
    logger.info("🦊 Инициализация базы данных...")
    await initialize_database()
    
    logger.info("📁 Создание папок для картинок (при необходимости)...")
    create_media_folders()
    
    logger.info("📚 Загрузка фраз из JSON...")
    load_phrases()
    
    # Передаём функции фраз в core
    set_phrase_functions(
        get_random_phrase,
        get_rank_phrase,
        get_streak_achievement
    )
    logger.info("✅ Функции фраз переданы в core")


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("🦊 Бот останавливается...")
    scheduler.shutdown()


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

async def main():
    """Главная функция запуска"""
    
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
        return
    
    storage = MemoryStorage()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    
    # ============================================================
    # РЕГИСТРАЦИЯ ХЕНДЛЕРОВ
    # ============================================================
    
    # 1. Админские команды (работают в ЛС и в чате)
    register_admin_handlers(dp)
    logger.info("✅ Админ-хендлеры зарегистрированы")
    
    # 2. Основные обработчики игрового чата
    register_handlers(dp)
    logger.info("✅ Основные хендлеры зарегистрированы")
    
    # ============================================================
    # КОМАНДЫ ДЛЯ МЕНЮ (ТОЛЬКО ПОЛЬЗОВАТЕЛЬСКИЕ!)
    # ============================================================
    
    await bot.set_my_commands([
        BotCommand(command="/start", description="Регистрация"),
        BotCommand(command="/name", description="Задать имя"),
        BotCommand(command="/me", description="Анкета"),
        BotCommand(command="/shop", description="Магазин"),
        BotCommand(command="/top_streak", description="Топ стриков"),
        BotCommand(command="/top_messages", description="Топ сообщений за сегодня"),
        BotCommand(command="/redemption", description="Прогресс восстановления стрика"),
    ])
    logger.info("✅ Команды в меню установлены (только пользовательские)")
    
    # ============================================================
    # ПЛАНИРОВЩИК
    # ============================================================
    
    scheduler.add_job(check_inactive_users, 'interval', minutes=30, args=(bot,), id='check_inactive')
    scheduler.add_job(check_expired_redemptions_task, 'interval', minutes=15, args=(bot,), id='check_redemptions')
    scheduler.add_job(daily_reset_and_reward, 'cron', hour=0, minute=0, timezone='Europe/Moscow', args=(bot,), id='daily_reset')
    scheduler.add_job(weekly_streak_reward, 'cron', day_of_week='sun', hour=23, minute=59, timezone='Europe/Moscow', args=(bot,), id='weekly_reward')
    scheduler.start()
    logger.info("🦊 Планировщик запущен")
    
    # ============================================================
    # ЗАПУСК
    # ============================================================
    
    await on_startup(bot)
    
    try:
        logger.info("🦊 Dori запущен и ждёт команды...")
        await dp.start_polling(bot)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
