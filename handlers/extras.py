"""
Extra features: reactions, leaderboard, anon chat, voice valentines, gifts, music, photos, chains
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, MessageHandler,
    ConversationHandler, filters
)

import database as db
from config import VOICE_PRICE, GIFT_PRICE, SCHEDULE_PRICE, PHOTO_PREMIUM_PRICE, VIRTUAL_GIFTS

REACTIONS = ["❤️", "😍", "🥰", "💕", "😘", "🔥", "💖", "✨"]

# Conversation states for media valentines
WAITING_VOICE_RECIPIENT, WAITING_VOICE_MSG = range(100, 102)
WAITING_PHOTO_RECIPIENT, WAITING_PHOTO_MSG = range(102, 104)


# ==================== LEADERBOARD ====================

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top senders and receivers"""
    query = update.callback_query
    await query.answer()

    top_receivers = await db.get_top_receivers(5)
    top_senders = await db.get_top_senders(5)

    text = "🏆 **ТОП ВАЛЕНТИНОК**\n\n"

    text += "💌 **Больше всего получили:**\n"
    for i, u in enumerate(top_receivers, 1):
        name = u['first_name'] or u['username'] or 'Аноним'
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — {u['count']} 💌\n"

    text += "\n💝 **Больше всего отправили:**\n"
    for i, u in enumerate(top_senders, 1):
        name = u['first_name'] or u['username'] or 'Аноним'
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — {u['count']} 💝\n"

    if not top_receivers and not top_senders:
        text += "\nПока нет данных. Будь первым! 🚀"

    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== REACTIONS ====================

async def show_reactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show reaction picker"""
    query = update.callback_query
    await query.answer()

    valentine_id = int(query.data.replace("react_", ""))

    keyboard = [
        [InlineKeyboardButton(r, callback_data=f"setreact_{valentine_id}_{r}") for r in REACTIONS[:4]],
        [InlineKeyboardButton(r, callback_data=f"setreact_{valentine_id}_{r}") for r in REACTIONS[4:]],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_inbox")]
    ]
    await query.edit_message_text(
        "Выбери реакцию на валентинку:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def set_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set reaction on valentine"""
    query = update.callback_query
    parts = query.data.replace("setreact_", "").split("_")
    valentine_id = int(parts[0])
    emoji = parts[1]

    await db.add_reaction(valentine_id, emoji)

    # Notify sender
    valentine = await db.get_valentine(valentine_id)
    if valentine:
        try:
            await context.bot.send_message(
                valentine['sender_id'],
                f"💫 На твою валентинку отреагировали: {emoji}"
            )
        except Exception:
            pass

    await query.answer(f"Реакция {emoji} добавлена!")

    from handlers.inbox import show_inbox
    await show_inbox(update, context, page=1)


# ==================== ANONYMOUS CHAT ====================

async def start_anon_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start anonymous chat with valentine sender"""
    query = update.callback_query
    await query.answer()

    valentine_id = int(query.data.replace("anonchat_", ""))
    valentine = await db.get_valentine(valentine_id)

    if not valentine:
        return

    # Create chat session
    chat_id = await db.create_anon_chat(valentine_id)

    context.user_data['anon_chat'] = chat_id
    context.user_data['anon_role'] = 'receiver'
    context.user_data['anon_valentine'] = valentine_id

    # Notify sender
    keyboard = [[InlineKeyboardButton("💬 Ответить", callback_data=f"joinchat_{chat_id}")]]
    await context.bot.send_message(
        valentine['sender_id'],
        "💬 Получатель твоей валентинки хочет пообщаться анонимно!\nНажми кнопку, чтобы начать чат.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await query.edit_message_text(
        "💬 **Анонимный чат начат!**\n\nПиши сообщения - они будут переданы отправителю анонимно.\n\nОтправь /endchat чтобы завершить.",
        parse_mode="Markdown"
    )


async def join_anon_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sender joins anonymous chat"""
    query = update.callback_query
    await query.answer()

    chat_id = query.data.replace("joinchat_", "")
    chat = await db.get_anon_chat(chat_id)

    if not chat:
        await query.answer("Чат не найден!", show_alert=True)
        return

    context.user_data['anon_chat'] = chat_id
    context.user_data['anon_role'] = 'sender'
    context.user_data['anon_valentine'] = chat['valentine_id']

    await query.edit_message_text(
        "💬 **Ты в анонимном чате!**\n\nПиши сообщения - получатель не узнает кто ты.\n\nОтправь /endchat чтобы завершить.",
        parse_mode="Markdown"
    )


async def handle_anon_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward message in anon chat"""
    chat_id = context.user_data.get('anon_chat')
    if not chat_id:
        return

    role = context.user_data.get('anon_role')
    valentine_id = context.user_data.get('anon_valentine')
    valentine = await db.get_valentine(valentine_id)

    if not valentine:
        return

    # Save message
    await db.save_anon_message(chat_id, role == 'sender', update.message.text)

    # Forward to other party
    target_id = valentine['sender_id'] if role == 'receiver' else valentine['receiver_id']
    prefix = "💌" if role == 'sender' else "💬"

    try:
        await context.bot.send_message(target_id, f"{prefix} {update.message.text}")
    except Exception:
        await update.message.reply_text("❌ Не удалось доставить сообщение")


# ==================== VOICE VALENTINES ====================

async def start_voice_valentine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start voice valentine flow"""
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_voice")]]

    await query.edit_message_text(
        "🎤 **ГОЛОСОВАЯ ВАЛЕНТИНКА**\n\n"
        "Запиши голосовое сообщение — бот отправит его анонимно!\n\n"
        f"💰 Стоимость: **{VOICE_PRICE}⭐**\n\n"
        "Сначала укажи @username получателя:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return WAITING_VOICE_RECIPIENT


async def voice_receive_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive recipient for voice valentine"""
    text = update.message.text.strip()
    if not text.startswith("@"):
        text = f"@{text}"

    recipient = await db.find_user_by_username(text)

    if not recipient:
        context.user_data['voice_recipient_username'] = text.lstrip('@')
        context.user_data['voice_recipient_id'] = None
    else:
        context.user_data['voice_recipient_id'] = recipient['user_id']
        context.user_data['voice_recipient_username'] = recipient['username']

    await update.message.reply_text(
        f"🎤 Получатель: **{text}**\n\n"
        "Теперь запиши и отправь **голосовое сообщение**:",
        parse_mode="Markdown"
    )
    return WAITING_VOICE_MSG


async def voice_receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive voice message"""
    voice = update.message.voice
    if not voice:
        await update.message.reply_text("❌ Отправь голосовое сообщение!")
        return WAITING_VOICE_MSG

    user = update.effective_user
    recipient_id = context.user_data.get('voice_recipient_id')

    # Create valentine with voice
    valentine_id = await db.create_valentine(
        sender_id=user.id,
        receiver_id=recipient_id,
        message="🎤 Голосовая валентинка",
        voice_file_id=voice.file_id
    )

    # Try to deliver
    if recipient_id:
        try:
            keyboard = [
                [InlineKeyboardButton(
                    "💫 Узнать кто отправил (50⭐)",
                    callback_data=f"reveal_{valentine_id}"
                )],
                [InlineKeyboardButton("◀️ В меню", callback_data="menu_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=recipient_id,
                text="🎤 **Тебе пришла голосовая валентинка!**\n\n❓ От тайного поклонника",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            await context.bot.send_voice(
                chat_id=recipient_id,
                voice=voice.file_id,
                caption="🎤 Анонимная голосовая валентинка!"
            )
            await db.mark_delivered(valentine_id)
        except Exception:
            pass

    # Use send slot
    await db.use_send_slot(user.id)

    # Check achievements
    from handlers.achievements import check_achievements
    await check_achievements(user.id, 'voice', context)

    keyboard = [[InlineKeyboardButton("◀️ Меню", callback_data="menu_main")]]
    await update.message.reply_text(
        "✅ **Голосовая валентинка отправлена!** 🎤",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel voice valentine"""
    query = update.callback_query
    await query.answer()
    from handlers.start import show_main_menu
    await show_main_menu(update, context)
    return ConversationHandler.END


# ==================== PHOTO VALENTINES ====================

async def start_photo_valentine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start photo valentine flow"""
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_photo")]]

    await query.edit_message_text(
        "📸 **ФОТО-ВАЛЕНТИНКА**\n\n"
        "Отправь фото — бот переправит его анонимно получателю!\n\n"
        "Сначала укажи @username получателя:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return WAITING_PHOTO_RECIPIENT


async def photo_receive_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive recipient for photo valentine"""
    text = update.message.text.strip()
    if not text.startswith("@"):
        text = f"@{text}"

    recipient = await db.find_user_by_username(text)

    if not recipient:
        context.user_data['photo_recipient_username'] = text.lstrip('@')
        context.user_data['photo_recipient_id'] = None
    else:
        context.user_data['photo_recipient_id'] = recipient['user_id']
        context.user_data['photo_recipient_username'] = recipient['username']

    await update.message.reply_text(
        f"📸 Получатель: **{text}**\n\n"
        "Теперь отправь **фото** для валентинки:",
        parse_mode="Markdown"
    )
    return WAITING_PHOTO_MSG


async def photo_receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive photo"""
    photo = update.message.photo
    if not photo:
        await update.message.reply_text("❌ Отправь фотографию!")
        return WAITING_PHOTO_MSG

    user = update.effective_user
    recipient_id = context.user_data.get('photo_recipient_id')
    photo_file_id = photo[-1].file_id  # Best quality

    # Create valentine with photo
    valentine_id = await db.create_valentine(
        sender_id=user.id,
        receiver_id=recipient_id,
        message="📸 Фото-валентинка",
        photo_file_id=photo_file_id
    )

    # Try to deliver
    if recipient_id:
        try:
            keyboard = [
                [InlineKeyboardButton(
                    "💫 Узнать кто отправил (50⭐)",
                    callback_data=f"reveal_{valentine_id}"
                )],
                [InlineKeyboardButton("◀️ В меню", callback_data="menu_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_photo(
                chat_id=recipient_id,
                photo=photo_file_id,
                caption="📸 **Тебе пришла фото-валентинка!**\n\n❓ От тайного поклонника",
                parse_mode="Markdown"
            )
            await context.bot.send_message(
                chat_id=recipient_id,
                text="Хочешь узнать, кто отправил?",
                reply_markup=reply_markup
            )
            await db.mark_delivered(valentine_id)
        except Exception:
            pass

    await db.use_send_slot(user.id)

    # Check achievements
    from handlers.achievements import check_achievements
    await check_achievements(user.id, 'photo', context)

    keyboard = [[InlineKeyboardButton("◀️ Меню", callback_data="menu_main")]]
    await update.message.reply_text(
        "✅ **Фото-валентинка отправлена!** 📸",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel photo valentine"""
    query = update.callback_query
    await query.answer()
    from handlers.start import show_main_menu
    await show_main_menu(update, context)
    return ConversationHandler.END


# ==================== VIRTUAL GIFTS ====================

async def show_gifts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show virtual gift picker"""
    query = update.callback_query
    await query.answer()

    valentine_id = query.data.replace("gift_pick_", "")
    context.user_data['gift_valentine_id'] = valentine_id

    keyboard = []
    gifts = list(VIRTUAL_GIFTS.items())
    for i in range(0, len(gifts), 4):
        row = [
            InlineKeyboardButton(f"{emoji} {name}", callback_data=f"gift_set_{valentine_id}_{emoji}")
            for emoji, name in gifts[i:i+4]
        ]
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="menu_main")])

    await query.edit_message_text(
        f"🎁 **Выбери подарок** ({GIFT_PRICE}⭐)\n\n"
        "Подарок будет прикреплён к валентинке!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def set_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set gift on valentine (create payment)"""
    query = update.callback_query
    await query.answer()

    parts = query.data.replace("gift_set_", "").rsplit("_", 1)
    valentine_id = parts[0]
    emoji = parts[1]

    context.user_data['gift_emoji'] = emoji
    context.user_data['gift_valentine_id'] = valentine_id

    prices = [LabeledPrice(label=f"Подарок {emoji}", amount=GIFT_PRICE)]

    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title=f"Подарок {emoji} {VIRTUAL_GIFTS.get(emoji, '')}",
        description="Прикрепить подарок к валентинке",
        payload=f"gift_{valentine_id}_{emoji}",
        currency="XTR",
        prices=prices,
    )


# ==================== MUSIC VALENTINE ====================

async def add_music_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt to add music link"""
    query = update.callback_query
    await query.answer()

    context.user_data['adding_music'] = True

    keyboard = [[InlineKeyboardButton("❌ Пропустить", callback_data="skip_music")]]
    await query.edit_message_text(
        "🎵 **Музыкальная валентинка**\n\n"
        "Отправь ссылку на песню (Spotify, YouTube, Яндекс.Музыка):\n\n"
        "Эта песня будет прикреплена к валентинке!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ==================== CHAIN VALENTINES ====================

async def show_chain_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show chain valentine progress"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    stats = await db.get_user_stats(user.id)
    chain = stats.get('chain', 0)

    from config import CHAIN_TARGET

    progress = min(chain, CHAIN_TARGET)
    bar = "🟥" * progress + "⬜" * (CHAIN_TARGET - progress)
    completed = chain >= CHAIN_TARGET

    text = (
        "⛓️ **ЦЕПОЧКА ВАЛЕНТИНОК**\n\n"
        f"Отправь {CHAIN_TARGET} валентинок друзьям — получи\n"
        f"🎁 **1 бесплатную премиум-валентинку!**\n\n"
        f"Прогресс: {bar} ({progress}/{CHAIN_TARGET})\n\n"
    )

    if completed:
        text += "✅ **Цепочка завершена!** Ты получил(а) бонус! 🎉"
    else:
        text += f"Осталось: **{CHAIN_TARGET - progress}** валентинок"

    keyboard = [
        [InlineKeyboardButton("💌 Отправить валентинку", callback_data="menu_send")],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ==================== SCHEDULE DELIVERY ====================

async def schedule_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for scheduled delivery"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🕛 14 фев, 00:00", callback_data="schedule_14_00")],
        [InlineKeyboardButton("🕗 14 фев, 08:00", callback_data="schedule_14_08")],
        [InlineKeyboardButton("🕐 14 фев, 12:00", callback_data="schedule_14_12")],
        [InlineKeyboardButton("🕕 14 фев, 18:00", callback_data="schedule_14_18")],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]
    ]

    await query.edit_message_text(
        f"⏰ **ОТЛОЖЕННАЯ ДОСТАВКА** ({SCHEDULE_PRICE}⭐)\n\n"
        "Выбери время доставки валентинки:\n\n"
        "💡 Валентинка будет доставлена точно в выбранное время!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def set_schedule_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set schedule time and create payment"""
    query = update.callback_query
    await query.answer()

    parts = query.data.replace("schedule_", "").split("_")
    day = int(parts[0])
    hour = int(parts[1])

    from datetime import datetime
    schedule_time = datetime(2026, 2, day, hour, 0, 0)
    context.user_data['schedule_time'] = schedule_time.isoformat()

    prices = [LabeledPrice(label="Отложенная доставка ⏰", amount=SCHEDULE_PRICE)]

    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title="Отложенная доставка ⏰",
        description=f"Доставка валентинки {day} февраля в {hour:02d}:00",
        payload=f"schedule_{query.from_user.id}",
        currency="XTR",
        prices=prices,
    )


def get_extra_handlers():
    """Return extra feature handlers"""
    voice_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_voice_valentine, pattern="^menu_voice$")],
        states={
            WAITING_VOICE_RECIPIENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, voice_receive_recipient),
            ],
            WAITING_VOICE_MSG: [
                MessageHandler(filters.VOICE, voice_receive_message),
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel_voice, pattern="^cancel_voice$")],
        per_message=False,
    )

    photo_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_photo_valentine, pattern="^menu_photo$")],
        states={
            WAITING_PHOTO_RECIPIENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, photo_receive_recipient),
            ],
            WAITING_PHOTO_MSG: [
                MessageHandler(filters.PHOTO, photo_receive_message),
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel_photo, pattern="^cancel_photo$")],
        per_message=False,
    )

    return [
        voice_conv,
        photo_conv,
        CallbackQueryHandler(show_leaderboard, pattern="^menu_top$"),
        CallbackQueryHandler(show_reactions, pattern=r"^react_\d+$"),
        CallbackQueryHandler(set_reaction, pattern="^setreact_"),
        CallbackQueryHandler(start_anon_chat, pattern=r"^anonchat_\d+$"),
        CallbackQueryHandler(join_anon_chat, pattern="^joinchat_"),
        CallbackQueryHandler(show_gifts, pattern="^gift_pick_"),
        CallbackQueryHandler(set_gift, pattern="^gift_set_"),
        CallbackQueryHandler(show_chain_progress, pattern="^menu_chain$"),
        CallbackQueryHandler(schedule_prompt, pattern="^menu_schedule$"),
        CallbackQueryHandler(set_schedule_time, pattern="^schedule_14_"),
    ]
