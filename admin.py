# admin.py

import os
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command

from config import is_admin, TRIGGER_NAMES, MOOD_NAMES, TRIGGER_EMOJI, MOOD_EMOJI, TRIGGER_SYMBOLS, MOOD_SYMBOLS
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
# 0. АДМИН-ПАНЕЛЬ
# ============================================================

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Только для администраторов.")
    
    await message.answer(
        "🦊 **Админ-панель Dori**\n\n"
        "Доступные команды:\n"
        "/coins — управление коинами\n"
        "/bypass — выдать щит\n"
        "/rank — управление рангами\n"
        "/phrase — добавить фразу\n"
        "/phrases — реестр фраз\n"
        "/pic — управление картинками\n"
        "/reload — перезагрузить кеш фраз"
    )


# ============================================================
# 1. УПРАВЛЕНИЕ КОИНАМИ
# ============================================================

@router.message(Command("coins"))
async def cmd_coins(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Только для администраторов.")
    
    text = message.text
    parts = text.split()
    
    if len(parts) < 4:
        return await message.answer(
            "📝 Используй: /coins give @username N\n"
            "/coins take @username N"
        )
    
    action = parts[1].lower()
    identifier = parts[2].replace('@', '')
    try:
        amount = float(parts[3])
    except ValueError:
        return await message.answer("❌ Сумма должна быть числом.")
    
    user = await get_user_by_identifier(identifier)
    if not user:
        return await message.answer("❌ Пользователь не найден.")
    
    await add_coins(user['user_id'], amount if action == 'give' else -amount)
    name = user.get('name', user.get('telegram_username', 'пользователя'))
    await message.answer(f"✅ {action} {amount} коинов для {name}")


# ============================================================
# 2. УПРАВЛЕНИЕ ЩИТАМИ
# ============================================================

@router.message(Command("bypass"))
async def cmd_bypass(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Только для администраторов.")
    
    text = message.text
    parts = text.split()
    
    if len(parts) < 3:
        return await message.answer(
            "📝 Используй: /bypass @username часы"
        )
    
    identifier = parts[1].replace('@', '')
    try:
        hours = int(parts[2])
    except ValueError:
        return await message.answer("❌ Часы должны быть числом.")
    
    user = await get_user_by_identifier(identifier)
    if not user:
        return await message.answer("❌ Пользователь не найден.")
    
    await set_shield(user['user_id'], hours)
    name = user.get('name', user.get('telegram_username', 'пользователя'))
    await message.answer(f"✅ Щит на {hours} часов для {name}")


# ============================================================
# 3. УПРАВЛЕНИЕ РАНГАМИ
# ============================================================

@router.message(Command("rank"))
async def cmd_rank(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Только для администраторов.")
    
    text = message.text
    parts = text.split()
    
    if len(parts) < 3:
        return await message.answer(
            "📝 Используй: /rank @username <ранг>"
        )
    
    identifier = parts[1].replace('@', '')
    rank_input = parts[2].strip()
    
    rank_map = {
        '0': 'Новичок', '1': 'Кандидат', '2': 'Знакомый',
        '3': 'Хороший', '4': 'Душа', '5': 'Старожил',
        '6': 'Гордость', '7': 'Авторитет', '8': 'Незаменимый'
    }
    
    if rank_input in rank_map:
        new_rank = rank_map[rank_input]
    else:
        new_rank = rank_input
    
    valid_ranks = ['Новичок', 'Кандидат', 'Знакомый', 'Хороший', 
                   'Душа', 'Старожил', 'Гордость', 'Авторитет', 'Незаменимый']
    if new_rank not in valid_ranks:
        return await message.answer(
            f"❌ Неверный ранг. Доступные: Новичок, Кандидат, Знакомый, Хороший, Душа, Старожил, Гордость, Авторитет, Незаменимый"
        )
    
    user = await get_user_by_identifier(identifier)
    if not user:
        return await message.answer("❌ Пользователь не найден.")
    
    async with aiosqlite.connect("dori.db") as db:
        await db.execute("UPDATE users SET rank = ? WHERE user_id = ?", (new_rank, user['user_id']))
        await db.commit()
    
    name = user.get('name', user.get('telegram_username', identifier))
    await message.answer(f"✅ Ранг изменён на '{new_rank}' для {name}")


# ============================================================
# 4. УПРАВЛЕНИЕ ФРАЗАМИ
# ============================================================

@router.message(Command("phrase"))
async def cmd_phrase_start(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Только для администраторов.")
    
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
        
        await message.reply(
            f"📝 **Фраза принята!**\n\n"
            f"**Триггер:** {TRIGGER_NAMES.get(parsed['trigger'], parsed['trigger'])}\n"
            f"**Поведение:** {MOOD_NAMES.get(parsed['mood'], parsed['mood'])}\n"
            f"**Текст:** {parsed['text']}\n\n"
            f"Все верно?",
            reply_markup=kb
        )


@router.callback_query(F.data == "phrase_confirm")
async def confirm_phrase(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in pending_phrases:
        return await callback.answer("❌ Сессия истекла", show_alert=True)
    
    data = pending_phrases.pop(user_id)
    success = confirm_add_phrase(data['trigger'], data['mood'], data['text'])
    
    if success:
        await callback.message.edit_text(
            f"✅ **Фраза добавлена!**\n\n"
            f"📌 {TRIGGER_NAMES.get(data['trigger'], data['trigger'])}\n"
            f"🎭 {MOOD_NAMES.get(data['mood'], data['mood'])}\n"
            f"📝 {data['text']}"
        )
        await callback.answer("✅ Фраза сохранена!")


@router.callback_query(F.data == "phrase_cancel")
async def cancel_phrase(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in pending_phrases:
        pending_phrases.pop(user_id)
    
    await callback.message.edit_text("❌ Добавление отменено")
    await callback.answer()


# ============================================================
# 4.1. ПРОСМОТР ФРАЗ (РЕЕСТР С ПАГИНАЦИЕЙ)
# ============================================================

@router.message(Command("phrases"))
async def cmd_phrases_main(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Только для администраторов.")
    
    all_phrases = get_all_phrases()
    if not all_phrases:
        return await message.reply("📭 Фраз пока нет. Добавь через /phrase")
    
    await show_phrases_page(message, all_phrases, 1)


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
    next_page = page + 1 if page < total_pages else 1
    
    buttons.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"phrases_page_{prev_page}"))
    buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="phrases_current"))
    buttons.append(InlineKeyboardButton(text="Вперед ▶", callback_data=f"phrases_page_{next_page}"))
    
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons])
    
    if edit_message_id:
        await message.bot.edit_message_text(text, chat_id=message.chat.id, message_id=edit_message_id, reply_markup=kb)
    else:
        await message.reply(text, reply_markup=kb)


@router.callback_query(F.data.startswith("phrases_page_"))
async def handle_phrases_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    all_phrases = get_all_phrases()
    await show_phrases_page(callback.message, all_phrases, page, edit_message_id=callback.message.message_id)
    await callback.answer()


# ============================================================
# 5. УПРАВЛЕНИЕ КАРТИНКАМИ
# ============================================================

@router.message(Command("pic"))
async def cmd_pic_start(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Только для администраторов.")
    
    stats = get_media_stats()
    total_pics = sum(stats.get('pics', {}).values())
    total_mems = sum(stats.get('mems', {}).values())
    
    trigger_buttons = []
    for symbol, trigger in TRIGGER_SYMBOLS.items():
        name = TRIGGER_NAMES.get(trigger, trigger)
        trigger_buttons.append([InlineKeyboardButton(text=f"{symbol} {name}", callback_data=f"pic_trigger_{trigger}")])
    trigger_buttons.append([InlineKeyboardButton(text="🌐 Все", callback_data="pic_trigger_all")])
    
    mood_buttons = []
    for symbol, mood in MOOD_SYMBOLS.items():
        name = MOOD_NAMES.get(mood, mood)
        mood_buttons.append([InlineKeyboardButton(text=f"{symbol} {name}", callback_data=f"pic_mood_{mood}")])
    mood_buttons.append([InlineKeyboardButton(text="🌐 Все", callback_data="pic_mood_all")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        *trigger_buttons,
        *mood_buttons,
        [InlineKeyboardButton(text=f"📂 Посмотреть ({total_pics + total_mems})", callback_data="pic_view")]
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
    trigger = callback.data.split("_")[2]
    if callback.from_user.id not in pending_pictures:
        pending_pictures[callback.from_user.id] = {}
    pending_pictures[callback.from_user.id]['trigger'] = trigger if trigger != 'all' else None
    await callback.answer(f"✅ Триггер выбран: {TRIGGER_NAMES.get(trigger, trigger) if trigger != 'all' else 'Все'}")
    await callback.message.edit_reply_markup(reply_markup=await get_picture_selection_kb(callback.from_user.id))


@router.callback_query(F.data.startswith("pic_mood_"))
async def pic_select_mood(callback: CallbackQuery):
    mood = callback.data.split("_")[2]
    if callback.from_user.id not in pending_pictures:
        pending_pictures[callback.from_user.id] = {}
    pending_pictures[callback.from_user.id]['mood'] = mood if mood != 'all' else None
    pending_pictures[callback.from_user.id]['is_meme'] = False
    await callback.answer(f"✅ Настроение выбрано: {MOOD_NAMES.get(mood, mood) if mood != 'all' else 'Все'}")
    await callback.message.edit_reply_markup(reply_markup=await get_picture_selection_kb(callback.from_user.id))


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


@router.callback_query(F.data == "pic_view")
async def pic_view(callback: CallbackQuery):
    data = pending_pictures.get(callback.from_user.id, {})
    if not data:
        return await callback.answer("❌ Сначала выбери триггер и настроение", show_alert=True)
    
    pictures = get_pictures_for_view(data.get('trigger'), data.get('mood'), data.get('is_meme', False))
    if not pictures:
        return await callback.answer("📭 Нет картинок по выбранным фильтрам", show_alert=True)
    
    picture_pagination[callback.from_user.id] = {'pictures': pictures, 'page': 1}
    await show_pictures_page(callback.message, pictures, 1, callback.from_user.id)


@router.callback_query(F.data.startswith("pic_page_"))
async def pic_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    data = picture_pagination.get(callback.from_user.id)
    if not data:
        return await callback.answer("❌ Сессия истекла", show_alert=True)
    await show_pictures_page(callback.message, data['pictures'], page, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "pic_delete")
async def pic_delete_start(callback: CallbackQuery):
    await callback.message.reply(
        "🗑 **Удаление картинки**\n\n"
        "Напиши номер картинки, которую хочешь удалить (1-10):"
    )
    await callback.answer()


@router.message(F.text.isdigit())
async def pic_delete_confirm(message: Message):
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
        f"📌 **Картинка #{index}:**\n\n```\n{file_path}\n```\n\nЧтобы удалить, скопируй путь и удали файл вручную.\n\n✅ Путь отправлен!"
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
    next_page = page + 1 if page < total_pages else 1
    buttons.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"pic_page_{prev_page}"))
    buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="pic_current"))
    buttons.append(InlineKeyboardButton(text="Вперед ▶", callback_data=f"pic_page_{next_page}"))
    buttons.append(InlineKeyboardButton(text="🗑 Удалить", callback_data="pic_delete"))
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons])
    
    if page_pictures:
        await message.bot.send_photo(
            message.chat.id,
            photo=FSInputFile(page_pictures[0]),
            caption=f"📸 **Страница {page}/{total_pages}**\n\nВсего: {len(pictures)} картинок\nПоказаны: {start + 1}-{min(end, len(pictures))}\n\nЧтобы удалить — нажми [🗑 Удалить] и введи номер.",
            reply_markup=kb
        )
    else:
        await message.reply("📭 Нет картинок на этой странице")


# ============================================================
# 6. ПЕРЕЗАГРУЗКА КЕША
# ============================================================

@router.message(Command("reload"))
async def cmd_reload(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("❌ Только для администраторов.")
    load_phrases()
    await message.reply("✅ Кеш фраз перезагружен из JSON!")


# ============================================================
# 7. РЕГИСТРАЦИЯ ХЕНДЛЕРОВ
# ============================================================

def register_admin_handlers(dp):
    dp.include_router(router)
