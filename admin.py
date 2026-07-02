# admin.py

import os
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command

from config import is_admin, ADMIN_IDS, CHAT_ID, TRIGGER_NAMES, MOOD_NAMES, TRIGGER_EMOJI, MOOD_EMOJI, TRIGGER_SYMBOLS, MOOD_SYMBOLS
from database import get_user_by_identifier, add_coins, set_shield
from phrases import (
    add_phrase_from_text, confirm_add_phrase,
    delete_phrase_by_global_index, get_all_phrases,
    get_filtered_phrases, get_trigger_from_alias,
    get_mood_from_alias, get_stats, load_phrases
)
from media import (
    get_media_stats, get_pictures_for_view,
    get_random_picture, get_folder_path,
    TRIGGER_CODE, MOOD_CODE
)

router = Router()

# ============================================================
# ХРАНИЛИЩЕ ВРЕМЕННЫХ ДАННЫХ
# ============================================================

pending_phrases = {}        # Для подтверждения фраз
pending_pictures = {}       # Для загрузки картинок
picture_pagination = {}     # Для пагинации картинок

# ============================================================
# 0. ТЕСТОВАЯ АДМИН-КОМАНДА ДЛЯ ПРОВЕРКИ
# ============================================================

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Простая команда для проверки работы админ-хендлеров"""
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Только для админов.")
    
    await message.answer(
        "✅ **Админ-панель активна**\n\n"
        "Доступные команды:\n"
        "• `.выдать @username N` — выдать коины\n"
        "• `.забрать @username N` — забирать коины\n"
        "• `.защита @username часы` — выдать щит\n"
        "• `.ранг @username <ранг>` — сменить ранг\n"
        "• `+фраза` — добавить фразу\n"
        "• `.фразы` — реестр фраз\n"
        "• `.фразы день` — фильтр по триггеру\n"
        "• `.фразы тревожное` — фильтр по настроению\n"
        "• `-фраза <номер>` — удалить фразу\n"
        "• `/pic` — управление картинками\n"
        "• `/reload` — перезагрузить кеш фраз"
    )


# ============================================================
# 1. УПРАВЛЕНИЕ КОИНАМИ
# ============================================================

@router.message(Command("coins"))
@router.message(F.text.lower().startswith(".выдать "))
@router.message(F.text.lower().startswith(".забрать "))
async def cmd_coins(message: Message):
    """Выдать или забрать коины у пользователя"""
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Ты не админ.")
    
    text = message.text
    parts = text.split()
    
    # Определяем действие
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
    
    # Определяем пользователя
    user = None
    if identifier:
        user = await get_user_by_identifier(identifier)
    else:
        if message.reply_to_message:
            user = await get_user_by_identifier(str(message.reply_to_message.from_user.id))
    
    if not user:
        return await message.answer("❌ Пользователь не найден.\nУкажи @username или ответь на сообщение.")
    
    # Применяем
    await add_coins(user['user_id'], amount if action == 'give' else -amount)
    name = user.get('name', user.get('telegram_username', 'пользователя'))
    await message.answer(f"✅ {action} {amount} коинов для {name} (ID: {user['user_id']})")


# ============================================================
# 2. УПРАВЛЕНИЕ ЩИТАМИ
# ============================================================

@router.message(Command("bypass"))
@router.message(F.text.lower().startswith(".защита "))
async def cmd_bypass(message: Message):
    """Выдать щит пользователю на N часов"""
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
    
    # Определяем пользователя
    user = None
    if identifier:
        user = await get_user_by_identifier(identifier)
    else:
        if message.reply_to_message:
            user = await get_user_by_identifier(str(message.reply_to_message.from_user.id))
    
    if not user:
        return await message.answer("❌ Пользователь не найден.\nУкажи @username или ответь на сообщение.")
    
    # Применяем
    await set_shield(user['user_id'], hours)
    name = user.get('name', user.get('telegram_username', 'пользователя'))
    await message.answer(f"✅ Щит на {hours} часов для {name} (ID: {user['user_id']})")


# ============================================================
# 3. УПРАВЛЕНИЕ РАНГАМИ
# ============================================================

@router.message(Command("rank"))
@router.message(F.text.lower().startswith(".ранг "))
async def cmd_rank(message: Message):
    """Принудительно меняет ранг пользователя"""
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Ты не админ.")
    
    text = message.text
    parts = text.split()
    
    # Маппинг цифр на ранги
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
    
    # Определяем пользователя
    user = await get_user_by_identifier(identifier)
    if not user:
        return await message.answer(f"❌ Пользователь '{identifier}' не найден.")
    
    # Определяем ранг
    if rank_input in rank_map:
        new_rank = rank_map[rank_input]
    else:
        new_rank = rank_input
    
    # Проверяем, что ранг существует
    valid_ranks = ['Новичок', 'Кандидат', 'Знакомый', 'Хороший', 
                   'Душа', 'Старожил', 'Гордость', 'Авторитет', 'Незаменимый']
    if new_rank not in valid_ranks:
        return await message.answer(
            f"❌ Неверный ранг: {new_rank}\n\n"
            f"Доступные ранги:\n"
            f"{chr(10).join('• ' + r for r in valid_ranks)}"
        )
    
    # Применяем
    async with aiosqlite.connect("dori.db") as db:
        await db.execute("UPDATE users SET rank = ? WHERE user_id = ?", (new_rank, user['user_id']))
        await db.commit()
    
    name = user.get('name', user.get('telegram_username', identifier))
    await message.answer(f"✅ Ранг изменён на '{new_rank}' для {name} (ID: {user['user_id']})")


# ============================================================
# 4. УПРАВЛЕНИЕ ФРАЗАМИ
# ============================================================

@router.message(Command("addphrase"))
@router.message(F.text.lower().startswith("+фраза"))
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


@router.message(F.text)
async def handle_phrase_input(message: Message):
    """Принимает фразу от админа (только если не команда)"""
    if not is_admin(message.from_user.id):
        return
    
    # Игнорируем команды
    if message.text.startswith('/') or message.text.startswith('.'):
        return
    
    # Проверяем, что сообщение начинается с символа триггера
    if message.text and message.text[0] in '!?~∆%':
        success, msg, parsed = add_phrase_from_text(message.text)
        
        if not success:
            return await message.reply(msg)
        
        # Сохраняем временно для подтверждения
        pending_phrases[message.from_user.id] = {
            'trigger': parsed['trigger'],
            'mood': parsed['mood'],
            'text': parsed['text']
        }
        
        # Клавиатура подтверждения
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


@router.callback_query(F.data == "phrase_confirm")
async def confirm_phrase(callback: CallbackQuery):
    """Подтверждает добавление фразы"""
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


@router.callback_query(F.data == "phrase_cancel")
async def cancel_phrase(callback: CallbackQuery):
    """Отменяет добавление фразы"""
    user_id = callback.from_user.id
    if user_id in pending_phrases:
        pending_phrases.pop(user_id)
    
    await callback.message.edit_text("❌ Добавление отменено")
    await callback.answer()


# ============================================================
# 4.1. ПРОСМОТР ФРАЗ (РЕЕСТР С ПАГИНАЦИЕЙ)
# ============================================================

@router.message(Command("phrases"))
@router.message(Command("фразы"))
@router.message(Command("phrase"))
@router.message(F.text.lower() == ".фразы")
async def cmd_phrases_main(message: Message):
    """Показывает реестр всех фраз"""
    if not is_admin(message.from_user.id):
        return
    
    all_phrases = get_all_phrases()
    
    if not all_phrases:
        return await message.reply("📭 Фраз пока нет. Добавь через `+фраза`")
    
    await show_phrases_page(message, all_phrases, 1)


@router.message(F.text.lower().startswith(".фразы "))
async def cmd_phrases_filtered(message: Message):
    """Показывает отфильтрованные фразы"""
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.lower().split()[1:]
    
    if not parts:
        return await cmd_phrases_main(message)
    
    # Парсим фильтры
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
    """Показывает страницу с фразами (15 шт.)"""
    PER_PAGE = 15
    total_pages = (len(phrases) + PER_PAGE - 1) // PER_PAGE
    
    if page < 1:
        page = total_pages
    if page > total_pages:
        page = 1
    
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_phrases = phrases[start:end]
    
    # Формируем текст
    text = f"📚 **РЕЕСТР ФРАЗ** (стр. {page}/{total_pages})\n\n"
    
    for p in page_phrases:
        trigger_emoji = TRIGGER_EMOJI.get(p['trigger'], '📌')
        mood_emoji = MOOD_EMOJI.get(p['mood'], '')
        
        text += f"{trigger_emoji}{mood_emoji} **{p['index']}.** {p['text']}\n"
    
    # Кнопки пагинации
    buttons = []
    
    prev_page = page - 1 if page > 1 else total_pages
    buttons.append(InlineKeyboardButton(
        text="◀ Назад",
        callback_data=f"phrases_page_{prev_page}"
    ))
    
    buttons.append(InlineKeyboardButton(
        text=f"{page}/{total_pages}",
        callback_data="phrases_current"
    ))
    
    next_page = page + 1 if page < total_pages else 1
    buttons.append(InlineKeyboardButton(
        text="Вперед ▶",
        callback_data=f"phrases_page_{next_page}"
    ))
    
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


@router.callback_query(F.data.startswith("phrases_page_"))
async def handle_phrases_page(callback: CallbackQuery):
    """Обработчик пагинации фраз"""
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


# ============================================================
# 4.2. УДАЛЕНИЕ ФРАЗЫ
# ============================================================

@router.message(Command("deletephrase"))
@router.message(F.text.lower().startswith("-фраза "))
async def cmd_delete_phrase(message: Message):
    """Удаляет фразу по номеру"""
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
# 5. УПРАВЛЕНИЕ КАРТИНКАМИ
# ============================================================

@router.message(Command("pic"))
@router.message(Command("фото"))
@router.message(Command("картинка"))
@router.message(Command("фотка"))
@router.message(F.text.lower() == ".фото")
@router.message(F.text.lower() == ".картинка")
async def cmd_add_picture_start(message: Message):
    """Начало добавления картинки"""
    if not is_admin(message.from_user.id):
        return
    
    # Получаем статистику
    stats = get_media_stats()
    total_pics = sum(stats.get('pics', {}).values())
    total_mems = sum(stats.get('mems', {}).values())
    
    # Кнопки выбора триггера
    trigger_buttons = []
    for symbol, trigger in TRIGGER_SYMBOLS.items():
        name = TRIGGER_NAMES.get(trigger, trigger)
        trigger_buttons.append([
            InlineKeyboardButton(
                text=f"{symbol} {name}",
                callback_data=f"pic_trigger_{trigger}"
            )
        ])
    trigger_buttons.append([
        InlineKeyboardButton(text="🌐 Все", callback_data="pic_trigger_all")
    ])
    
    # Кнопки выбора настроения
    mood_buttons = []
    for symbol, mood in MOOD_SYMBOLS.items():
        name = MOOD_NAMES.get(mood, mood)
        mood_buttons.append([
            InlineKeyboardButton(
                text=f"{symbol} {name}",
                callback_data=f"pic_mood_{mood}"
            )
        ])
    mood_buttons.append([
        InlineKeyboardButton(text="🌐 Все", callback_data="pic_mood_all")
    ])
    
    # Общая клавиатура
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


@router.callback_query(F.data.startswith("pic_trigger_"))
async def pic_select_trigger(callback: CallbackQuery):
    """Выбор триггера для картинки"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Только админы!", show_alert=True)
    
    trigger = callback.data.split("_")[2]
    
    # Сохраняем выбор
    if callback.from_user.id not in pending_pictures:
        pending_pictures[callback.from_user.id] = {}
    pending_pictures[callback.from_user.id]['trigger'] = trigger if trigger != 'all' else None
    
    await callback.answer(f"✅ Триггер выбран: {TRIGGER_NAMES.get(trigger, trigger) if trigger != 'all' else 'Все'}")
    
    # Обновляем сообщение
    await callback.message.edit_reply_markup(
        reply_markup=await get_picture_selection_kb(callback.from_user.id)
    )


@router.callback_query(F.data.startswith("pic_mood_"))
async def pic_select_mood(callback: CallbackQuery):
    """Выбор настроения для картинки"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Только админы!", show_alert=True)
    
    mood = callback.data.split("_")[2]
    
    # Сохраняем выбор
    if callback.from_user.id not in pending_pictures:
        pending_pictures[callback.from_user.id] = {}
    pending_pictures[callback.from_user.id]['mood'] = mood if mood != 'all' else None
    pending_pictures[callback.from_user.id]['is_meme'] = False  # По умолчанию pics
    
    await callback.answer(f"✅ Настроение выбрано: {MOOD_NAMES.get(mood, mood) if mood != 'all' else 'Все'}")
    
    # Обновляем сообщение
    await callback.message.edit_reply_markup(
        reply_markup=await get_picture_selection_kb(callback.from_user.id)
    )


async def get_picture_selection_kb(user_id: int) -> InlineKeyboardMarkup:
    """Возвращает обновлённую клавиатуру выбора картинки"""
    data = pending_pictures.get(user_id, {})
    trigger = data.get('trigger')
    mood = data.get('mood')
    
    # Определяем, что выбрано
    trigger_name = TRIGGER_NAMES.get(trigger, 'Не выбран') if trigger else 'Все'
    mood_name = MOOD_NAMES.get(mood, 'Не выбрано') if mood else 'Все'
    
    # Кнопки
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"📂 Посмотреть ({trigger_name} | {mood_name})",
                callback_data="pic_view"
            )
        ],
        [
            InlineKeyboardButton(
                text="📤 Отправить фото",
                callback_data="pic_send"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Сбросить выбор",
                callback_data="pic_reset"
            )
        ]
    ])
    
    return kb


@router.callback_query(F.data == "pic_view")
async def pic_view(callback: CallbackQuery):
    """Показывает картинки с пагинацией"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Только админы!", show_alert=True)
    
    data = pending_pictures.get(callback.from_user.id, {})
    trigger = data.get('trigger')
    mood = data.get('mood')
    is_meme = data.get('is_meme', False)
    
    # Получаем картинки
    pictures = get_pictures_for_view(trigger, mood, is_meme)
    
    if not pictures:
        return await callback.answer("📭 Нет картинок по выбранным фильтрам", show_alert=True)
    
    # Сохраняем для пагинации
    picture_pagination[callback.from_user.id] = {
        'pictures': pictures,
        'page': 1
    }
    
    await show_pictures_page(callback.message, pictures, 1, callback.from_user.id)


@router.callback_query(F.data.startswith("pic_page_"))
async def pic_page(callback: CallbackQuery):
    """Пагинация картинок"""
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


@router.callback_query(F.data == "pic_delete")
async def pic_delete_start(callback: CallbackQuery):
    """Начало удаления картинки"""
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Только админы!", show_alert=True)
    
    await callback.message.reply(
        "🗑 **Удаление картинки**\n\n"
        "Напиши номер картинки, которую хочешь удалить (1-10):"
    )
    await callback.answer()


@router.message(F.text.isdigit())
async def pic_delete_confirm(message: Message):
    """Подтверждение удаления картинки"""
    if not is_admin(message.from_user.id):
        return
    
    # Проверяем, есть ли активная сессия просмотра
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
    
    # Получаем путь к файлу
    file_path = pictures[index - 1]
    
    # Отправляем путь в ЛС
    await message.bot.send_message(
        message.from_user.id,
        f"📌 **Картинка #{index}:**\n\n"
        f"```\n{file_path}\n```\n\n"
        f"Чтобы удалить, скопируй путь и удали файл вручную.\n\n"
        f"✅ Путь отправлен!"
    )
    
    await message.reply(f"✅ Путь к картинке #{index} отправлен в ЛС!")


async def show_pictures_page(message: Message, pictures: list, page: int, user_id: int):
    """Показывает страницу с картинками (10 шт.)"""
    PER_PAGE = 10
    total_pages = (len(pictures) + PER_PAGE - 1) // PER_PAGE
    
    if page < 1:
        page = total_pages
    if page > total_pages:
        page = 1
    
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_pictures = pictures[start:end]
    
    # Сохраняем текущую страницу
    picture_pagination[user_id]['page'] = page
    
    # Кнопки пагинации
    buttons = []
    
    prev_page = page - 1 if page > 1 else total_pages
    buttons.append(InlineKeyboardButton(
        text="◀ Назад",
        callback_data=f"pic_page_{prev_page}"
    ))
    
    buttons.append(InlineKeyboardButton(
        text=f"{page}/{total_pages}",
        callback_data="pic_current"
    ))
    
    next_page = page + 1 if page < total_pages else 1
    buttons.append(InlineKeyboardButton(
        text="Вперед ▶",
        callback_data=f"pic_page_{next_page}"
    ))
    
    buttons.append(InlineKeyboardButton(
        text="🗑 Удалить",
        callback_data="pic_delete"
    ))
    
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons])
    
    # Отправляем первую картинку как пример
    # Для простоты показываем только первую
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


# ============================================================
# 6. ПЕРЕЗАГРУЗКА КЕША
# ============================================================

@router.message(Command("reload"))
@router.message(F.text.lower() == ".перезагрузить")
async def cmd_reload(message: Message):
    """Перезагружает кеш фраз из JSON"""
    if not is_admin(message.from_user.id):
        return
    
    load_phrases()
    await message.reply("✅ Кеш фраз перезагружен из JSON!")


# ============================================================
# 7. РЕГИСТРАЦИЯ ХЕНДЛЕРОВ (ДЛЯ MAIN.PY)
# ============================================================

def register_admin_handlers(dp):
    """Регистрирует все админ-команды"""
    dp.include_router(router)
