# core.py

import os
import random
import logging
import aiosqlite
from datetime import datetime, timedelta
from aiogram import F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command

from database import (
    register_user, get_user, update_user_name, update_last_message,
    add_coins, set_shield, update_streak, get_user_by_identifier,
    get_inactive_users, increment_streak,
    increment_messages_today,
    start_redemption, update_redemption_progress,
    get_redemption_status, complete_redemption,
    add_reward_history,
    add_shield, use_shield, get_shield_count
)

from config import CHAT_ID, ADMIN_CHAT_ID, ADMIN_IDS, is_admin, is_allowed_chat, TRIGGER_NAMES, MOOD_NAMES, TRIGGER_EMOJI, MOOD_EMOJI
from phrases import (
    add_phrase_from_text, confirm_add_phrase,
    delete_phrase_by_global_index, get_all_phrases,
    get_filtered_phrases, get_trigger_from_alias,
    get_mood_from_alias, get_stats, load_phrases,
    get_random_phrase, get_rank_phrase, get_streak_achievement
)
from media import (
    get_media_stats, get_pictures_for_view,
    get_random_picture, get_folder_path
)

logger = logging.getLogger(__name__)

# ============================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ ФУНКЦИЙ ИЗ PHRASES
# ============================================================

_get_random_phrase = None
_get_rank_phrase = None
_get_streak_achievement = None


def set_phrase_functions(get_random, get_rank, get_streak):
    """Устанавливает функции из phrases.py"""
    global _get_random_phrase, _get_rank_phrase, _get_streak_achievement
    _get_random_phrase = get_random
    _get_rank_phrase = get_rank
    _get_streak_achievement = get_streak


def get_random_phrase_async(trigger: str, mood: str = None) -> str | None:
    if _get_random_phrase:
        return _get_random_phrase(trigger, mood)
    return None


def get_rank_phrase_async(rank_name: str) -> str | None:
    if _get_rank_phrase:
        return _get_rank_phrase(rank_name)
    return None


def get_streak_achievement_async(day: int) -> str | None:
    if _get_streak_achievement:
        return _get_streak_achievement(day)
    return None


# ============================================================
# 🔥 ФИЛЬТР ПРОВЕРКИ ЧАТА
# ============================================================

def chat_filter(message: Message) -> bool:
    """Разрешает работу в основном чате, чате админов и ЛС"""
    if message.chat.type == "private":
        return True
    return message.chat.id in [CHAT_ID, ADMIN_CHAT_ID]


# ============================================================
# РЕГИСТРАЦИЯ ХЕНДЛЕРОВ
# ============================================================

def register_handlers(dp):
    """Регистрирует ВСЕ команды (пользовательские + админские)"""
    
    # ========================
    # ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ
    # ========================
    
    dp.message.register(cmd_start, Command("start"), chat_filter)
    dp.message.register(cmd_name, Command("name"), chat_filter)
    dp.message.register(cmd_name, F.text.lower().startswith(".имя "), chat_filter)
    dp.message.register(cmd_me, Command("me"), chat_filter)
    dp.message.register(cmd_me, Command("profile"), chat_filter)
    dp.message.register(cmd_me, F.text.lower() == ".я", chat_filter)
    dp.message.register(cmd_me, F.text.lower() == ".профиль", chat_filter)
    dp.message.register(cmd_shop, Command("shop"), chat_filter)
    dp.message.register(cmd_shop, F.text.lower() == ".шоп", chat_filter)
    dp.message.register(cmd_shop, F.text.lower() == ".щит", chat_filter)
    dp.message.register(cmd_redemption, Command("redemption"), chat_filter)
    dp.message.register(cmd_redemption, F.text.lower() == ".искупление", chat_filter)
    
    dp.message.register(cmd_top_streak, Command("top_streak"), chat_filter)
    dp.message.register(cmd_top_streak, F.text.lower() == ".топ стрик", chat_filter)
    dp.message.register(cmd_top_streak, F.text.lower() == "топ стрик", chat_filter)
    dp.message.register(cmd_top_messages, Command("top_messages"), chat_filter)
    dp.message.register(cmd_top_messages, F.text.lower() == ".топ соо", chat_filter)
    dp.message.register(cmd_top_messages, F.text.lower() == "топ соо", chat_filter)
    
    dp.message.register(process_message, chat_filter)
    dp.callback_query.register(process_shop, F.data.in_(["buy_shield", "use_shield"]))
    
    # ========================
    # АДМИНСКИЕ КОМАНДЫ
    # ========================
    
    dp.message.register(cmd_coins, Command("coins"), chat_filter)
    dp.message.register(cmd_coins, F.text.lower().startswith(".выдать "), chat_filter)
    dp.message.register(cmd_coins, F.text.lower().startswith(".забрать "), chat_filter)
    dp.message.register(cmd_bypass, Command("bypass"), chat_filter)
    dp.message.register(cmd_bypass, F.text.lower().startswith(".защита "), chat_filter)
    dp.message.register(cmd_rank, Command("rank"), chat_filter)
    dp.message.register(cmd_rank, F.text.lower().startswith(".ранг "), chat_filter)
    dp.message.register(cmd_add_phrase_start, Command("addphrase"), chat_filter)
    dp.message.register(cmd_add_phrase_start, F.text.lower().startswith("+фраза"), chat_filter)
    dp.message.register(handle_phrase_input, F.text, chat_filter)
    dp.message.register(cmd_phrases_main, Command("phrases"), chat_filter)
    dp.message.register(cmd_phrases_main, Command("фразы"), chat_filter)
    dp.message.register(cmd_phrases_main, Command("phrase"), chat_filter)
    dp.message.register(cmd_phrases_main, F.text.lower() == ".фразы"), chat_filter)
    dp.message.register(cmd_phrases_filtered, F.text.lower().startswith(".фразы "), chat_filter)
    dp.message.register(cmd_delete_phrase, Command("deletephrase"), chat_filter)
    dp.message.register(cmd_delete_phrase, F.text.lower().startswith("-фраза "), chat_filter)
    dp.message.register(cmd_add_picture_start, Command("pic"), chat_filter)
    dp.message.register(cmd_add_picture_start, Command("фото"), chat_filter)
    dp.message.register(cmd_add_picture_start, Command("картинка"), chat_filter)
    dp.message.register(cmd_add_picture_start, Command("фотка"), chat_filter)
    dp.message.register(cmd_add_picture_start, F.text.lower() == ".фото", chat_filter)
    dp.message.register(cmd_add_picture_start, F.text.lower() == ".картинка", chat_filter)
    dp.message.register(cmd_reload, Command("reload"), chat_filter)
    dp.message.register(cmd_reload, F.text.lower() == ".перезагрузить", chat_filter)
    
    dp.callback_query.register(confirm_phrase, F.data == "phrase_confirm")
    dp.callback_query.register(cancel_phrase, F.data == "phrase_cancel")
    dp.callback_query.register(pic_select_trigger, F.data.startswith("pic_trigger_"))
    dp.callback_query.register(pic_select_mood, F.data.startswith("pic_mood_"))
    dp.callback_query.register(pic_view, F.data == "pic_view")
    dp.callback_query.register(pic_page, F.data.startswith("pic_page_"))
    dp.callback_query.register(pic_delete_start, F.data == "pic_delete")
    dp.callback_query.register(handle_phrases_page, F.data.startswith("phrases_page_"))


# ============================================================
# ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ
# ============================================================

async def cmd_start(message: Message):
    user = await get_user(message.from_user.id)
    
    if not user:
        await register_user(message.from_user.id, message.from_user.username)
        
        if is_admin(message.from_user.id):
            await message.answer(
                "Добрый день, администратор 🦊\n\n"
                "Вы успешно зарегистрированы в системе.\n\n"
                "Используйте /me для просмотра анкеты."
            )
        else:
            await message.answer(
                "🦊 Привет! Я Dori — Архитектор Дисциплины!\n"
                "Ты зарегистрировался\n\n"
                "Используй /name чтобы задать себе имя, или /me для просмотра анкеты."
            )
        return
    
    if is_admin(message.from_user.id):
        await message.answer(
            "Добрый день, администратор 🦊\n\n"
            "Используйте /me для просмотра анкеты."
        )
    else:
        await message.answer(
            "🦊 Привет! Я Dori — Архитектор Дисциплины!\n\n"
            "/me - профиль\n"
            "/shop - магазин\n"
            ".топ стрик - топ стриков\n"
            ".топ соо - топ сообщений за сегодня\n"
            ".искупление - прогресс восстановления стрика"
        )


async def cmd_name(message: Message):
    text = message.text
    if text.startswith("/name"):
        args = text.split(maxsplit=1)
    elif text.lower().startswith(".имя "):
        args = [".имя", text[5:].strip()]
    else:
        return
    
    if len(args) < 2:
        return await message.answer("Используй: /name ТвоёИмя или .имя ТвоёИмя")
    
    new_name = args[1].strip()
    if len(new_name) > 50:
        return await message.answer("❌ Имя слишком длинное (макс. 50 символов).")
    
    success = await update_user_name(message.from_user.id, new_name)
    if success:
        await message.answer(f"✅ Теперь ты {new_name}!")
    else:
        await message.answer("❌ Это имя уже занято. Выбери другое.")


async def cmd_me(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала зарегистрируйся: /start")
    
    shield_status = "❌ Не активен"
    if user['shield_until']:
        try:
            shield_time = datetime.fromisoformat(user['shield_until'])
            if shield_time > datetime.now():
                hours_left = (shield_time - datetime.now()).total_seconds() / 3600
                shield_status = f"🛡️ Активен ({int(hours_left)} ч.)"
            else:
                shield_status = "❌ Истёк"
        except:
            pass
    
    shield_count = await get_shield_count(message.from_user.id)
    
    redemption = await get_redemption_status(message.from_user.id)
    redemption_text = ""
    if redemption and redemption['active']:
        progress = redemption['progress']
        target = redemption['target']
        redemption_text = f"\n| 🔄 Искупление: {progress}/{target} сообщений"
    
    text = (
        f"📋 Анкета {user['name'] or 'Без имени'}\n"
        f"| Ранг: {user['rank']}\n"
        f"| Стриков: {user['streak']} дней\n"
        f"| Рекорд: {user['streak_record']} дней\n"
        f"| Коинов: {user['coins']:.1f}\n"
        f"| Щитов: {shield_count} шт.\n"
        f"| Щит: {shield_status}{redemption_text}"
    )
    await message.answer(text)


async def cmd_shop(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала зарегистрируйся: /start")
    
    shield_count = await get_shield_count(message.from_user.id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🛡️ Купить щит (100 коинов) [{shield_count} шт.]", callback_data="buy_shield")],
        [InlineKeyboardButton(text="⚡ Активировать щит (36 часов)", callback_data="use_shield")]
    ])
    await message.answer(
        f"🛒 **Магазин**\n\n"
        f"💰 Коинов: {user['coins']:.1f}\n"
        f"🛡️ Щитов в запасе: {shield_count} шт.\n\n"
        f"💡 Щит защищает стрик от сброса на 36 часов",
        reply_markup=kb
    )


async def process_shop(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        return await callback.answer("Сначала зарегистрируйся: /start", show_alert=True)
    
    if callback.data == "buy_shield":
        if user['coins'] < 100:
            return await callback.answer("❌ Недостаточно коинов! Нужно 100.", show_alert=True)
        
        await add_coins(callback.from_user.id, -100)
        await add_shield(callback.from_user.id, 1)
        
        shield_count = await get_shield_count(callback.from_user.id)
        
        await callback.answer("✅ Щит куплен!", show_alert=True)
        await callback.message.edit_text(
            f"✅ Щит куплен!\n\n"
            f"🛡️ Теперь у тебя {shield_count} щитов.\n"
            f"Используй 'Активировать щит', чтобы защитить стрик."
        )
    
    elif callback.data == "use_shield":
        shield_count = await get_shield_count(callback.from_user.id)
        if shield_count == 0:
            return await callback.answer("❌ У тебя нет щитов! Купи в магазине.", show_alert=True)
        
        if user['shield_until']:
            try:
                shield_time = datetime.fromisoformat(user['shield_until'])
                if shield_time > datetime.now():
                    hours_left = (shield_time - datetime.now()).total_seconds() / 3600
                    return await callback.answer(
                        f"⏳ У тебя уже активен щит ({int(hours_left)} ч.)", 
                        show_alert=True
                    )
            except:
                pass
        
        await use_shield(callback.from_user.id)
        await set_shield(callback.from_user.id, 36)
        
        shield_count = await get_shield_count(callback.from_user.id)
        
        await callback.answer("⚡ Щит активирован на 36 часов!", show_alert=True)
        await callback.message.edit_text(
            f"🛡️ Щит активирован на 36 часов!\n\n"
            f"Осталось щитов: {shield_count} шт."
        )


async def cmd_top_streak(message: Message):
    from database import get_top_streak
    top = await get_top_streak(15)
    
    if not top:
        return await message.answer("📊 Пока нет данных. Напиши что-нибудь!")
    
    text = "🏆 **ТОП СТРИКОВ**\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, user in enumerate(top):
        medal = medals[i] if i < 10 else f"{i+1}."
        name = user.get('name', user.get('telegram_username', 'Без имени'))
        text += f"{medal} **{name}** — {user['streak']} дней\n"
    
    text += "\n✨ **Награды в конце недели:**\n🥇 10000 | 🥈 5000 | 🥉 1000 коинов"
    await message.answer(text)


async def cmd_top_messages(message: Message):
    from database import get_top_messages_today
    top = await get_top_messages_today(15)
    
    if not top:
        return await message.answer("📊 Сегодня пока никто не писал. Будь первым!")
    
    text = "💬 **ТОП СООБЩЕНИЙ** (за сегодня)\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, user in enumerate(top):
        medal = medals[i] if i < 10 else f"{i+1}."
        name = user.get('name', user.get('telegram_username', 'Без имени'))
        text += f"{medal} **{name}** — {user['messages_today']} сообщений\n"
    
    text += "\n✨ **1 место** получит 100 коинов в 00:00 МСК!"
    await message.answer(text)


async def cmd_redemption(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала зарегистрируйся: /start")
    
    redemption = await get_redemption_status(message.from_user.id)
    
    if not redemption or not redemption['active']:
        return await message.answer(
            "❌ У тебя нет активного искупления.\n"
            "Оно появляется, если ты потерял стрик."
        )
    
    progress = redemption['progress']
    target = redemption['target']
    streak_to_restore = redemption['streak_to_restore']
    remaining = target - progress
    
    try:
        expires = datetime.fromisoformat(redemption['expires_at'])
        hours_left = (expires - datetime.now()).total_seconds() / 3600
    except:
        hours_left = 24
    
    text = (
        f"🔄 **Восстановление стрика**\n\n"
        f"Цель: {target} сообщений\n"
        f"Прогресс: {progress} сообщений\n"
        f"Осталось: {remaining} сообщений\n"
        f"Восстановится стрик: {streak_to_restore} дней\n"
        f"⏳ Осталось: ~{int(hours_left)} часов\n\n"
        f"{'🔥 ДАВАЙ, ТЫ СМОЖЕШЬ!' if progress > 100 else '💪 ПИШИ БОЛЬШЕ!'}"
    )
    await message.answer(text)


async def process_message(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        return
    
    await update_last_message(message.from_user.id)
    await add_coins(message.from_user.id, 0.1)
    await increment_messages_today(message.from_user.id)
    
    current_streak = user['streak'] or 0
    
    # --- ИСКУПЛЕНИЕ ---
    redemption = await get_redemption_status(message.from_user.id)
    if redemption and redemption['active']:
        await update_redemption_progress(message.from_user.id)
        
        updated = await get_redemption_status(message.from_user.id)
        progress = updated['progress']
        target = updated['target']
        streak_to_restore = updated['streak_to_restore']
        
        if progress >= target:
            await complete_redemption(message.from_user.id)
            name = user.get('name', user.get('telegram_username', 'Кто-то'))
            await message.answer(
                f"🎉 **{name}** восстановил стрик в {streak_to_restore} дней! 🦊"
            )
            await message.bot.send_message(
                CHAT_ID,
                f"🎉 **{name}** восстановил стрик в {streak_to_restore} дней! 🔥"
            )
            return
        else:
            if progress % 50 == 0:
                remaining = target - progress
                await message.answer(
                    f"📊 {progress}/{target} сообщений до восстановления. Осталось {remaining}!"
                )
    
    # --- ПРОВЕРКА РАНГОВ ---
    rank_mapping = {
        0: "Новичок", 2: "Кандидат", 5: "Знакомый",
        9: "Хороший", 16: "Душа", 24: "Старожил",
        34: "Гордость", 47: "Авторитет", 60: "Незаменимый"
    }
    
    for min_streak, rank_name in sorted(rank_mapping.items()):
        if current_streak >= min_streak and user['rank'] != rank_name:
            async with aiosqlite.connect("dori.db") as db:
                await db.execute("UPDATE users SET rank = ? WHERE user_id = ?", (rank_name, user['user_id']))
                await db.commit()
            
            rank_phrase = get_rank_phrase_async(rank_name)
            if rank_phrase:
                await message.answer(f"🏆 Поздравляю! Ты достиг ранга {rank_name}!\n\n{rank_phrase}")
            else:
                await message.answer(f"🏆 Поздравляю! Ты достиг ранга {rank_name}!")
            break
    
    # --- ДОСТИЖЕНИЯ ---
    achievement_days = [7, 14, 31, 99, 356]
    if current_streak in achievement_days:
        async with aiosqlite.connect("dori.db") as db:
            cursor = await db.execute(
                "SELECT 1 FROM rewards_history WHERE user_id = ? AND reward_type = 'achievement' AND streak = ?",
                (user['user_id'], current_streak)
            )
            already = await cursor.fetchone()
        
        if not already:
            phrase = get_streak_achievement_async(current_streak)
            if not phrase:
                phrase = f"Ты достиг {current_streak} дней стрика! 🦊"
            
            name = user.get('name', user.get('telegram_username', 'Кто-то'))
            await message.bot.send_message(
                CHAT_ID,
                f"🎉 **{name}** заработал {current_streak}-дневный стрик!\n\n{phrase}"
            )
            await add_reward_history(user['user_id'], 'achievement', 0, 0, current_streak)
    
    # --- ОБНОВЛЕНИЕ СТРИКА ---
    if user['last_message']:
        try:
            last_msg_time = datetime.fromisoformat(user['last_message'])
            if datetime.now() - last_msg_time > timedelta(hours=24):
                new_streak = await increment_streak(message.from_user.id)
                if new_streak in [5, 10, 25, 50, 100]:
                    await message.answer(f"🎉 {new_streak} дней подряд! Ты крут!")
        except:
            pass


# ============================================================
# АДМИНСКИЕ КОМАНДЫ
# ============================================================

async def cmd_coins(message: Message):
    """Выдать или забрать коины"""
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Ты не админ.")
    
    text = message.text
    parts = text.split()
    
    if text.startswith("/coins"):
        if len(parts) < 4:
            return await message.answer(
                "📝 Используй:\n"
                "/coins give @username N\n"
                "/coins take @username N\n"
                "Или с ответом на сообщение:\n"
                "/coins give N"
            )
        action = parts[1].lower()
        identifier = parts[2].replace('@', '')
        try:
            amount = float(parts[3])
        except ValueError:
            return await message.answer("❌ Сумма должна быть числом.")
    elif text.lower().startswith(".выдать "):
        if len(parts) < 2:
            return await message.answer("📝 Используй: .выдать @username N")
        if parts[1].lstrip('@').isdigit():
            try:
                amount = float(parts[1])
            except ValueError:
                return await message.answer("❌ Сумма должна быть числом.")
            identifier = None
            action = 'give'
        else:
            identifier = parts[1].replace('@', '')
            try:
                amount = float(parts[2])
            except ValueError:
                return await message.answer("❌ Сумма должна быть числом.")
            action = 'give'
    elif text.lower().startswith(".забрать "):
        if len(parts) < 2:
            return await message.answer("📝 Используй: .забрать @username N")
        if parts[1].lstrip('@').isdigit():
            try:
                amount = float(parts[1])
            except ValueError:
                return await message.answer("❌ Сумма должна быть числом.")
            identifier = None
            action = 'take'
        else:
            identifier = parts[1].replace('@', '')
            try:
                amount = float(parts[2])
            except ValueError:
                return await message.answer("❌ Сумма должна быть числом.")
            action = 'take'
    else:
        return
    
    user = None
    if identifier:
        user = await get_user_by_identifier(identifier)
    else:
        if message.reply_to_message:
            user = await get_user_by_identifier(str(message.reply_to_message.from_user.id))
    
    if not user:
        return await message.answer("❌ Пользователь не найден.\nУкажи @username или ответь на сообщение.")
    
    await add_coins(user['user_id'], amount if action == 'give' else -amount)
    name = user.get('name', user.get('telegram_username', 'пользователя'))
    await message.answer(f"✅ {action} {amount} коинов для {name} (ID: {user['user_id']})")


async def cmd_bypass(message: Message):
    """Выдать щит на N часов"""
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Ты не админ.")
    
    text = message.text
    parts = text.split()
    
    if text.startswith("/bypass"):
        if len(parts) < 3:
            return await message.answer(
                "📝 Используй:\n"
                "/bypass @username часы\n"
                "Или с ответом на сообщение:\n"
                "/bypass часы"
            )
        identifier = parts[1].replace('@', '')
        try:
            hours = int(parts[2])
        except ValueError:
            return await message.answer("❌ Часы должны быть числом.")
    elif text.lower().startswith(".защита "):
        if len(parts) < 2:
            return await message.answer(
                "📝 Используй:\n"
                ".защита @username часы\n"
                "Или с ответом на сообщение:\n"
                ".защита часы"
            )
        if parts[1].isdigit():
            try:
                hours = int(parts[1])
            except ValueError:
                return await message.answer("❌ Часы должны быть числом.")
            identifier = None
        else:
            identifier = parts[1].replace('@', '')
            try:
                hours = int(parts[2])
            except ValueError:
                return await message.answer("❌ Часы должны быть числом.")
    else:
        return
    
    user = None
    if identifier:
        user = await get_user_by_identifier(identifier)
    else:
        if message.reply_to_message:
            user = await get_user_by_identifier(str(message.reply_to_message.from_user.id))
    
    if not user:
        return await message.answer("❌ Пользователь не найден.\nУкажи @username или ответь на сообщение.")
    
    await set_shield(user['user_id'], hours)
    name = user.get('name', user.get('telegram_username', 'пользователя'))
    await message.answer(f"✅ Щит на {hours} часов для {name} (ID: {user['user_id']})")


async def cmd_rank(message: Message):
    """Принудительно меняет ранг"""
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Ты не админ.")
    
    text = message.text
    parts = text.split()
    
    rank_map = {
        '0': 'Новичок',
        '1': 'Кандидат',
        '2': 'Знакомый',
        '3': 'Хороший',
        '4': 'Душа',
        '5': 'Старожил',
        '6': 'Гордость',
        '7': 'Авторитет',
        '8': 'Незаменимый'
    }
    
    if text.startswith("/rank"):
        if len(parts) < 3:
            return await message.answer(
                "📝 Используй:\n"
                "/rank @username <название_ранга>\n"
                "/rank @username <0-8>\n\n"
                "0 - Новичок\n"
                "1 - Кандидат\n"
                "2 - Знакомый\n"
                "3 - Хороший\n"
                "4 - Душа\n"
                "5 - Старожил\n"
                "6 - Гордость\n"
                "7 - Авторитет\n"
                "8 - Незаменимый"
            )
        identifier = parts[1].replace('@', '')
        rank_input = parts[2].strip()
    elif text.lower().startswith(".ранг "):
        if len(parts) < 3:
            return await message.answer(
                "📝 Используй:\n"
                ".ранг @username <название_ранга>\n"
                ".ранг @username <0-8>\n\n"
                "0 - Новичок\n"
                "1 - Кандидат\n"
                "2 - Знакомый\n"
                "3 - Хороший\n"
                "4 - Душа\n"
                "5 - Старожил\n"
                "6 - Гордость\n"
                "7 - Авторитет\n"
                "8 - Незаменимый"
            )
        identifier = parts[1].replace('@', '')
        rank_input = parts[2].strip()
    else:
        return
    
    user = await get_user_by_identifier(identifier)
    if not user:
        return await message.answer(f"❌ Пользователь '{identifier}' не найден.")
    
    if rank_input in rank_map:
        new_rank = rank_map[rank_input]
    else:
        new_rank = rank_input
    
    valid_ranks = ['Новичок', 'Кандидат', 'Знакомый', 'Хороший', 
                   'Душа', 'Старожил', 'Гордость', 'Авторитет', 'Незаменимый']
    if new_rank not in valid_ranks:
        return await message.answer(
            f"❌ Неверный ранг: {new_rank}\n\n"
            f"Доступные ранги:\n"
            f"{chr(10).join('• ' + r for r in valid_ranks)}"
        )
    
    async with aiosqlite.connect("dori.db") as db:
        await db.execute("UPDATE users SET rank = ? WHERE user_id = ?", (new_rank, user['user_id']))
        await db.commit()
    
    name = user.get('name', user.get('telegram_username', identifier))
    await message.answer(f"✅ Ранг изменён на '{new_rank}' для {name} (ID: {user['user_id']})")


# ============================================================
# АДМИНСКИЕ КОМАНДЫ ДЛЯ ФРАЗ
# ============================================================

pending_phrases = {}  # Для подтверждения фраз

async def cmd_add_phrase_start(message: Message):
    """Начало добавления фразы"""
    if not is_admin(message.from_user.id):
        return
    
    await message.reply(
        "📝 **Отправьте фразу по регламенту:**\n\n"
        "Формат: `!₽ Текст фразы`\n\n"
        "**Триггеры (первый символ):**\n"
        "`!` — 1 день неактива\n"
        "`?` — 2+ дней неактива\n"
        "`~` — Возвращение\n"
        "`∆` — Ранги\n"
        "`%` — Достижения стрика\n\n"
        "**Настроения (второй символ):**\n"
        "`₽` — Тревожное 😰\n"
        "`£` — Злое 😡\n"
        "`€` — Саркастичное 😏\n"
        "`$` — Мотивирующее 💪\n"
        "`¢` — Дружелюбное 🤗\n\n"
        "Пример: `!$ Ты куда пропал? Мы уже все углы прочекали! 🤣`"
    )


async def handle_phrase_input(message: Message):
    """Принимает фразу от админа"""
    if not is_admin(message.from_user.id):
        return
    
    if message.text.startswith('/') or message.text.startswith('.'):
        return
    
    if message.text and message.text[0] in '!?~∆%':
        success, msg, parsed = add_phrase_from_text(message.text)
        
        if not success:
            return await message.reply(msg)
        
        pending_phrases[message.from_user.id] = {
            'trigger': parsed['trigger'],
            'mood': parsed['mood'],
            'text': parsed['text']
        }
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data="phrase_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="phrase_cancel")
            ]
        ])
        
        trigger_name = TRIGGER_NAMES.get(parsed['trigger'], parsed['trigger'])
        mood_name = MOOD_NAMES.get(parsed['mood'], parsed['mood'])
        
        await message.reply(
            f"📝 **Фраза принята!**\n\n"
            f"**Триггер:** {trigger_name}\n"
            f"**Поведение:** {mood_name}\n"
            f"**Текст:** {parsed['text']}\n\n"
            f"Все верно?",
            reply_markup=kb
        )


async def confirm_phrase(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in pending_phrases:
        return await callback.answer("❌ Сессия истекла, отправьте фразу заново", show_alert=True)
    
    data = pending_phrases.pop(user_id)
    success = confirm_add_phrase(data['trigger'], data['mood'], data['text'])
    
    if success:
        trigger_name = TRIGGER_NAMES.get(data['trigger'], data['trigger'])
        mood_name = MOOD_NAMES.get(data['mood'], data['mood'])
        
        await callback.message.edit_text(
            f"✅ **Фраза добавлена!**\n\n"
            f"📌 {trigger_name}\n"
            f"🎭 {mood_name}\n"
            f"📝 {data['text']}"
        )
        await callback.answer("✅ Фраза сохранена!")
    else:
        await callback.answer("❌ Ошибка сохранения", show_alert=True)


async def cancel_phrase(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in pending_phrases:
        pending_phrases.pop(user_id)
    
    await callback.message.edit_text("❌ Добавление отменено")
    await callback.answer()


async def cmd_phrases_main(message: Message):
    """Реестр всех фраз"""
    if not is_admin(message.from_user.id):
        return
    
    all_phrases = get_all_phrases()
    
    if not all_phrases:
        return await message.reply("📭 Фраз пока нет. Добавь через `+фраза`")
    
    await show_phrases_page(message, all_phrases, 1)


async def cmd_phrases_filtered(message: Message):
    """Фильтрованный реестр"""
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.lower().split()[1:]
    
    if not parts:
        return await cmd_phrases_main(message)
    
    trigger = None
    mood = None
    unknown = []
    
    for part in parts:
        t = get_trigger_from_alias(part)
        if t:
            trigger = t
            continue
        
        m = get_mood_from_alias(part)
        if m:
            mood = m
            continue
        
        unknown.append(part)
    
    if unknown:
        return await message.reply(
            f"❌ Неизвестные фильтры: {', '.join(unknown)}\n\n"
            f"Доступные триггеры: день, несколько, ранг, возвращение, призыв\n"
            f"Доступные поведения: тревожное, злое, саркастичное, мотивирующее, дружелюбное"
        )
    
    filtered = get_filtered_phrases(trigger, mood)
    
    if not filtered:
        filter_desc = []
        if trigger:
            filter_desc.append(TRIGGER_NAMES.get(trigger, trigger))
        if mood:
            filter_desc.append(MOOD_NAMES.get(mood, mood))
        
        return await message.reply(f"📭 Нет фраз по фильтру: {', '.join(filter_desc)}")
    
    await show_phrases_page(message, filtered, 1)


async def show_phrases_page(message: Message, phrases: list, page: int, edit_message_id: int = None):
    PER_PAGE = 15
    total_pages = (len(phrases) + PER_PAGE - 1) // PER_PAGE
    
    if page < 1:
        page = total_pages
    if page > total_pages:
        page = 1
    
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_phrases = phrases[start:end]
    
    text = f"📚 **РЕЕСТР ФРАЗ** (стр. {page}/{total_pages})\n\n"
    
    for p in page_phrases:
        trigger_emoji = TRIGGER_EMOJI.get(p['trigger'], '📌')
        mood_emoji = MOOD_EMOJI.get(p['mood'], '')
        
        text += f"{trigger_emoji}{mood_emoji} **{p['index']}.** {p['text']}\n"
    
    buttons = []
    prev_page = page - 1 if page > 1 else total_pages
    buttons.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"phrases_page_{prev_page}"))
    buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="phrases_current"))
    next_page = page + 1 if page < total_pages else 1
    buttons.append(InlineKeyboardButton(text="Вперед ▶", callback_data=f"phrases_page_{next_page}"))
    
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons])
    
    if edit_message_id:
        await message.bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=edit_message_id,
            reply_markup=kb
        )
    else:
        await message.reply(text, reply_markup=kb)


async def handle_phrases_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Только админы!", show_alert=True)
    
    page = int(callback.data.split("_")[2])
    all_phrases = get_all_phrases()
    
    await show_phrases_page(
        callback.message,
        all_phrases,
        page,
        edit_message_id=callback.message.message_id
    )
    await callback.answer()


async def cmd_delete_phrase(message: Message):
    """Удалить фразу по номеру"""
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("📝 Используй: `-фраза <номер>`")
    
    try:
        index = int(parts[1].strip())
    except ValueError:
        return await message.reply("❌ Номер должен быть числом")
    
    success, msg = delete_phrase_by_global_index(index)
    await message.reply(msg)


# ============================================================
# АДМИНСКИЕ КОМАНДЫ ДЛЯ КАРТИНОК
# ============================================================

pending_pictures = {}
picture_pagination = {}

async def cmd_add_picture_start(message: Message):
    """Начало добавления картинки"""
    if not is_admin(message.from_user.id):
        return
    
    stats = get_media_stats()
    total_pics = sum(stats.get('pics', {}).values())
    total_mems = sum(stats.get('mems', {}).values())
    
    trigger_buttons = []
    for symbol, trigger in TRIGGER_SYMBOLS.items():
        name = TRIGGER_NAMES.get(trigger, trigger)
        trigger_buttons.append([
            InlineKeyboardButton(text=f"{symbol} {name}", callback_data=f"pic_trigger_{trigger}")
        ])
    trigger_buttons.append([InlineKeyboardButton(text="🌐 Все", callback_data="pic_trigger_all")])
    
    mood_buttons = []
    for symbol, mood in MOOD_SYMBOLS.items():
        name = MOOD_NAMES.get(mood, mood)
        mood_buttons.append([
            InlineKeyboardButton(text=f"{symbol} {name}", callback_data=f"pic_mood_{mood}")
        ])
    mood_buttons.append([InlineKeyboardButton(text="🌐 Все", callback_data="pic_mood_all")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        *trigger_buttons,
        *mood_buttons,
        [
            InlineKeyboardButton(
                text=f"📂 Посмотреть ({total_pics + total_mems})",
                callback_data="pic_view"
            )
        ]
    ])
    
    await message.reply(
        f"📸 **Добавление картинки**\n\n"
        f"📊 Картинок: {total_pics}\n"
        f"📊 Мемов: {total_mems}\n\n"
        f"Выбери триггер и настроение, затем отправь фото.",
        reply_markup=kb
    )


async def pic_select_trigger(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Только админы!", show_alert=True)
    
    trigger = callback.data.split("_")[2]
    
    if callback.from_user.id not in pending_pictures:
        pending_pictures[callback.from_user.id] = {}
    pending_pictures[callback.from_user.id]['trigger'] = trigger if trigger != 'all' else None
    
    await callback.answer(f"✅ Триггер выбран: {TRIGGER_NAMES.get(trigger, trigger) if trigger != 'all' else 'Все'}")
    await callback.message.edit_reply_markup(
        reply_markup=await get_picture_selection_kb(callback.from_user.id)
    )


async def pic_select_mood(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Только админы!", show_alert=True)
    
    mood = callback.data.split("_")[2]
    
    if callback.from_user.id not in pending_pictures:
        pending_pictures[callback.from_user.id] = {}
    pending_pictures[callback.from_user.id]['mood'] = mood if mood != 'all' else None
    pending_pictures[callback.from_user.id]['is_meme'] = False
    
    await callback.answer(f"✅ Настроение выбрано: {MOOD_NAMES.get(mood, mood) if mood != 'all' else 'Все'}")
    await callback.message.edit_reply_markup(
        reply_markup=await get_picture_selection_kb(callback.from_user.id)
    )


async def get_picture_selection_kb(user_id: int) -> InlineKeyboardMarkup:
    data = pending_pictures.get(user_id, {})
    trigger = data.get('trigger')
    mood = data.get('mood')
    
    trigger_name = TRIGGER_NAMES.get(trigger, 'Не выбран') if trigger else 'Все'
    mood_name = MOOD_NAMES.get(mood, 'Не выбрано') if mood else 'Все'
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📂 Посмотреть ({trigger_name} | {mood_name})", callback_data="pic_view")],
        [InlineKeyboardButton(text="📤 Отправить фото", callback_data="pic_send")],
        [InlineKeyboardButton(text="🔄 Сбросить выбор", callback_data="pic_reset")]
    ])
    
    return kb


async def pic_view(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Только админы!", show_alert=True)
    
    data = pending_pictures.get(callback.from_user.id, {})
    trigger = data.get('trigger')
    mood = data.get('mood')
    is_meme = data.get('is_meme', False)
    
    pictures = get_pictures_for_view(trigger, mood, is_meme)
    
    if not pictures:
        return await callback.answer("📭 Нет картинок по выбранным фильтрам", show_alert=True)
    
    picture_pagination[callback.from_user.id] = {
        'pictures': pictures,
        'page': 1
    }
    
    await show_pictures_page(callback.message, pictures, 1, callback.from_user.id)


async def pic_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Только админы!", show_alert=True)
    
    page = int(callback.data.split("_")[2])
    data = picture_pagination.get(callback.from_user.id)
    
    if not data:
        return await callback.answer("❌ Сессия истекла, начните заново", show_alert=True)
    
    await show_pictures_page(
        callback.message,
        data['pictures'],
        page,
        callback.from_user.id
    )
    await callback.answer()


async def pic_delete_start(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Только админы!", show_alert=True)
    
    await callback.message.reply(
        "🗑 **Удаление картинки**\n\n"
        "Напиши номер картинки, которую хочешь удалить (1-10):"
    )
    await callback.answer()


async def pic_delete_confirm(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    data = picture_pagination.get(message.from_user.id)
    if not data:
        return
    
    try:
        index = int(message.text)
    except ValueError:
        return await message.reply("❌ Введи число")
    
    pictures = data['pictures']
    if index < 1 or index > len(pictures):
        return await message.reply(f"❌ Введи число от 1 до {len(pictures)}")
    
    file_path = pictures[index - 1]
    
    await message.bot.send_message(
        message.from_user.id,
        f"📌 **Картинка #{index}:**\n\n"
        f"```\n{file_path}\n```\n\n"
        f"Чтобы удалить, скопируй путь и удали файл вручную.\n\n"
        f"✅ Путь отправлен!"
    )
    
    await message.reply(f"✅ Путь к картинке #{index} отправлен в ЛС!")


async def show_pictures_page(message: Message, pictures: list, page: int, user_id: int):
    PER_PAGE = 10
    total_pages = (len(pictures) + PER_PAGE - 1) // PER_PAGE
    
    if page < 1:
        page = total_pages
    if page > total_pages:
        page = 1
    
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_pictures = pictures[start:end]
    
    picture_pagination[user_id]['page'] = page
    
    buttons = []
    prev_page = page - 1 if page > 1 else total_pages
    buttons.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"pic_page_{prev_page}"))
    buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="pic_current"))
    next_page = page + 1 if page < total_pages else 1
    buttons.append(InlineKeyboardButton(text="Вперед ▶", callback_data=f"pic_page_{next_page}"))
    buttons.append(InlineKeyboardButton(text="🗑 Удалить", callback_data="pic_delete"))
    
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons])
    
    if page_pictures:
        await message.bot.send_photo(
            message.chat.id,
            photo=FSInputFile(page_pictures[0]),
            caption=f"📸 **Страница {page}/{total_pages}**\n\n"
                    f"Всего: {len(pictures)} картинок\n"
                    f"Показаны: {start + 1}-{min(end, len(pictures))}\n\n"
                    f"Чтобы удалить — нажми [🗑 Удалить] и введи номер.",
            reply_markup=kb
        )
    else:
        await message.reply("📭 Нет картинок на этой странице")


async def cmd_reload(message: Message):
    """Перезагрузка кеша фраз"""
    if not is_admin(message.from_user.id):
        return
    
    load_phrases()
    await message.reply("✅ Кеш фраз перезагружен из JSON!")


# ============================================================
# ПЛАНИРОВЩИК (ВЫЗЫВАЕТСЯ ИЗ MAIN.PY)
# ============================================================

async def check_inactive_users(bot: Bot):
    inactive = await get_inactive_users()
    
    chat_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗣 В чат", url="https://t.me/Gar3mDi")]
    ])
    
    for user in inactive:
        if not user['last_message']:
            continue
        
        hours_since = (datetime.now() - datetime.fromisoformat(user['last_message'])).total_seconds() / 3600
        
        if 24 <= hours_since < 48:
            phrase = get_random_phrase_async("1_DAY_INACTIVE")
            if phrase:
                await bot.send_message(user['user_id'], phrase, reply_markup=chat_button)
            else:
                await bot.send_message(user['user_id'], "📣 Ты пропал на сутки. Напиши что-нибудь!", reply_markup=chat_button)
        
        elif hours_since >= 48:
            shield_active = user['shield_until'] and datetime.fromisoformat(user['shield_until']) > datetime.now()
            
            if shield_active:
                await set_shield(user['user_id'], 0)
                await bot.send_message(
                    user['user_id'],
                    "🛡️ Щит спас стрик! Но он сгорел. Купи новый в /shop.",
                    reply_markup=chat_button
                )
            else:
                old_streak = user['streak']
                await update_streak(user['user_id'], 0, user['streak_record'])
                await start_redemption(user['user_id'], old_streak)
                
                name = user.get('name', user.get('telegram_username', 'Кто-то'))
                
                await bot.send_message(
                    user['user_id'],
                    f"💔 Стрик в {old_streak} дней сброшен.\n\n"
                    f"🔄 **Шанс восстановить!**\n"
                    f"Напиши **200 сообщений** за сегодня!\n\n"
                    f"Прогресс: **.искупление**",
                    reply_markup=chat_button
                )
                
                await bot.send_message(
                    CHAT_ID,
                    f"😱 **{name}** проиграл стрик в {old_streak} дней!\n"
                    f"Но может восстановить — 200 сообщений за сегодня. 👀"
                )
                
                if random.choice([True, False]):
                    picture = await get_random_picture("2_PLUS_DAYS_INACTIVE", "SARCASTIC", is_meme=True)
                    if not picture:
                        picture = await get_random_picture("2_PLUS_DAYS_INACTIVE", "SARCASTIC", is_meme=False)
                    
                    if picture:
                        await bot.send_photo(user['user_id'], photo=FSInputFile(picture), reply_markup=chat_button)
                    else:
                        phrase = get_random_phrase_async("2_PLUS_DAYS_INACTIVE")
                        if phrase:
                            await bot.send_message(user['user_id'], phrase, reply_markup=chat_button)


async def daily_reset_and_reward(bot: Bot):
    from database import award_daily_top, reset_daily_messages
    winner = await award_daily_top()
    if winner:
        name = winner.get('name', winner.get('telegram_username', 'Кто-то'))
        await bot.send_message(CHAT_ID, f"🌟 **{name}** лидер по сообщениям! +100 коинов! 🪙")
    await reset_daily_messages()
    logger.info("🔄 Daily reset")


async def weekly_streak_reward(bot: Bot):
    from database import award_weekly_top
    winners = await award_weekly_top()
    if winners:
        text = "🏆 **ЕЖЕНЕДЕЛЬНЫЙ ТОП**\n\n"
        for user, pos, coins in winners:
            name = user.get('name', user.get('telegram_username', 'Кто-то'))
            medal = ["🥇", "🥈", "🥉"][pos - 1]
            text += f"{medal} **{name}** — {user['streak']} дней (+{coins} коинов)\n"
        await bot.send_message(CHAT_ID, text)
        logger.info("🔄 Weekly rewards")


async def check_expired_redemptions_task(bot: Bot):
    from database import check_expired_redemptions, get_user
    expired = await check_expired_redemptions()
    for user_id in expired:
        user = await get_user(user_id)
        if user:
            name = user.get('name', user.get('telegram_username', 'Кто-то'))
            await bot.send_message(
                user_id,
                f"💀 Время вышло. Стрик не восстановлен. Начинай с нуля, {name}! 💪"
            )
            await bot.send_message(
                CHAT_ID,
                f"⏰ **{name}** не успел восстановить стрик. Начинает с нуля. 😈"
  )
