"""
Valentine sending handlers with ConversationHandler v2.0
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, filters
)

import database as db
from config import MAX_MESSAGE_LENGTH, BUNDLE_PRICE, BOT_USERNAME, CHAIN_TARGET, REVEAL_PRICE
from templates import (
    RECIPIENT_PROMPT_TEXT, MESSAGE_PROMPT_TEXT, CONFIRM_SEND_TEXT,
    VALENTINE_SENT_TEXT, format_valentine, VALENTINE_RECEIVED_TEXT,
    VALENTINE_TEMPLATES, QUICK_REPLIES
)

# Conversation states
WAITING_RECIPIENT, WAITING_MESSAGE, CONFIRM_SEND = range(3)


async def start_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start sending valentine flow"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    # Check if user can send
    can_send = await db.can_send_free(user.id)

    if not can_send:
        from config import WEEKLY_BUNDLE_PRICE, SUB_ROMANTIC_PRICE
        keyboard = [
            [InlineKeyboardButton(
                f"🎁 Недельный бандл — {WEEKLY_BUNDLE_PRICE}⭐ (20 посланий)",
                callback_data="buy_weekbundle"
            )],
            [InlineKeyboardButton(
                f"💎 Пакет 5 посланий — {BUNDLE_PRICE}⭐",
                callback_data="buy_bundle"
            )],
            [InlineKeyboardButton(
                f"⭐ Premium Romantic — {SUB_ROMANTIC_PRICE}⭐/мес",
                callback_data="menu_premium"
            )],
            [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "⚠️ **Дневной лимит исчерпан!**\n\n"
            "Бесплатные послания на сегодня закончились.\n\n"
            "Выбери вариант:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_send")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        RECIPIENT_PROMPT_TEXT,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    return WAITING_RECIPIENT


async def receive_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process recipient input"""
    user = update.effective_user
    msg = update.message

    # Check if forwarded message (v21+ uses forward_origin)
    forward_origin = getattr(msg, 'forward_origin', None)

    if forward_origin:
        from telegram import MessageOriginUser
        if isinstance(forward_origin, MessageOriginUser):
            recipient = forward_origin.sender_user
            recipient_id = recipient.id
            recipient_name = recipient.first_name
            recipient_username = recipient.username

            await db.get_or_create_user(
                user_id=recipient_id,
                username=recipient_username,
                first_name=recipient_name
            )
        else:
            await msg.reply_text("❌ Не могу определить отправителя. Введи @username")
            return WAITING_RECIPIENT
    elif msg.text:
        text = msg.text.strip()
        if text.startswith("@"):
            username = text
        else:
            username = f"@{text}"

        recipient_user = await db.find_user_by_username(username)

        if not recipient_user:
            # User not in bot - will deliver via link
            context.user_data['recipient_id'] = None
            context.user_data['recipient_name'] = username
            context.user_data['recipient_username'] = username.lstrip('@')
            context.user_data['recipient_not_in_bot'] = True

            keyboard = [
                [InlineKeyboardButton(f"💬 {t[:25]}...", callback_data=f"template_{i}")]
                for i, t in enumerate(QUICK_REPLIES)
            ]
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_send")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await msg.reply_text(
                f"💌 Получатель: **{username}**\n\n"
                f"⚠️ Этот человек ещё не в боте — ты получишь ссылку для него!\n\n"
                f"✍️ Напиши текст валентинки:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return WAITING_MESSAGE

        recipient_id = recipient_user['user_id']
        recipient_name = recipient_user['first_name'] or username
        recipient_username = recipient_user['username']
        context.user_data['recipient_not_in_bot'] = False
    else:
        await msg.reply_text("❌ Введи @username получателя")
        return WAITING_RECIPIENT

    # Check not sending to self
    if recipient_id == user.id:
        await update.message.reply_text(
            "😅 Нельзя отправить валентинку самому себе!\n"
            "Укажи другого получателя."
        )
        return WAITING_RECIPIENT

    # Store recipient info
    context.user_data['recipient_id'] = recipient_id
    context.user_data['recipient_name'] = recipient_name
    context.user_data['recipient_username'] = recipient_username

    # Show template suggestions
    keyboard = [
        [InlineKeyboardButton(f"💬 {t[:30]}...", callback_data=f"template_{i}")]
        for i, t in enumerate(QUICK_REPLIES)
    ]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_send")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    display_name = f"@{recipient_username}" if recipient_username else recipient_name

    await update.message.reply_text(
        f"💌 Получатель: **{display_name}**\n\n{MESSAGE_PROMPT_TEXT}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    return WAITING_MESSAGE


async def use_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Use selected template"""
    query = update.callback_query
    await query.answer()

    template_idx = int(query.data.replace("template_", ""))
    if template_idx < len(QUICK_REPLIES):
        message = QUICK_REPLIES[template_idx]
    else:
        message = VALENTINE_TEMPLATES[template_idx % len(VALENTINE_TEMPLATES)]

    context.user_data['valentine_message'] = message

    return await show_preview(update, context, from_callback=True)


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process valentine message text"""
    message = update.message.text

    if len(message) > MAX_MESSAGE_LENGTH:
        await update.message.reply_text(
            f"❌ Сообщение слишком длинное!\n"
            f"Максимум {MAX_MESSAGE_LENGTH} символов, у тебя {len(message)}."
        )
        return WAITING_MESSAGE

    context.user_data['valentine_message'] = message

    return await show_preview(update, context, from_callback=False)


async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback: bool):
    """Show valentine preview"""
    message = context.user_data['valentine_message']
    recipient_name = context.user_data.get('recipient_name', '???')
    recipient_username = context.user_data.get('recipient_username', '')
    formatted = format_valentine(message, is_premium=False)

    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить", callback_data="confirm_send"),
            InlineKeyboardButton("✏️ Редактировать", callback_data="edit_message"),
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_send")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    display_name = f"@{recipient_username}" if recipient_username else recipient_name

    text = (
        f"👁 **Предпросмотр:**\n\n"
        f"📩 Кому: **{display_name}**\n"
        f"💬 Текст: {formatted}\n\n"
        f"Отправить?"
    )

    if from_callback:
        await update.callback_query.edit_message_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    return CONFIRM_SEND


async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and send valentine"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    recipient_id = context.user_data.get('recipient_id')
    message = context.user_data['valentine_message']
    music_url = context.user_data.get('music_url')
    schedule_time = context.user_data.get('schedule_time') if context.user_data.get('schedule_active') else None

    # Use send slot
    await db.use_send_slot(user.id)

    # Create valentine
    valentine_id = await db.create_valentine(
        sender_id=user.id,
        receiver_id=recipient_id,
        message=message,
        music_url=music_url,
        scheduled_for=schedule_time
    )

    # Increment chain
    chain_count = await db.increment_chain(user.id)

    # Check chain achievement
    from handlers.achievements import check_achievements
    if chain_count >= CHAIN_TARGET:
        await check_achievements(user.id, 'chain', context)
        # Grant bonus valentine
        if chain_count == CHAIN_TARGET:
            await db.add_bonus_valentines(user.id, 1)

    # Check send achievement
    await check_achievements(user.id, 'send', context)
    if music_url:
        await check_achievements(user.id, 'music', context)

    # Deliver
    if schedule_time:
        # Scheduled delivery
        context.user_data.clear()

        keyboard = [[InlineKeyboardButton("◀️ В меню", callback_data="menu_main")]]
        await query.edit_message_text(
            f"⏰ **Валентинка запланирована!**\n\n"
            f"Будет доставлена в назначенное время.\n"
            f"Ты получишь уведомление! 🔔",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    direct_delivery = False
    if recipient_id:
        try:
            await deliver_valentine(context, valentine_id, recipient_id, message, music_url)
            await db.mark_delivered(valentine_id)
            direct_delivery = True
        except Exception:
            pass

    # Clean up
    context.user_data.clear()

    if direct_delivery:
        text = VALENTINE_SENT_TEXT.format(reveal_price=REVEAL_PRICE)
    else:
        share_link = f"https://t.me/{BOT_USERNAME}?start=valentine_{valentine_id}"
        text = (
            f"💌 Валентинка создана!\n\n"
            f"Получатель ещё не в боте. Отправь ему ссылку:\n"
            f"`{share_link}`"
        )

    keyboard = [[InlineKeyboardButton("◀️ В меню", callback_data="menu_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text, reply_markup=reply_markup, parse_mode="Markdown"
    )

    return ConversationHandler.END


async def deliver_valentine(context: ContextTypes.DEFAULT_TYPE, valentine_id: int,
                           recipient_id: int, message: str, music_url: str = None):
    """Deliver valentine to recipient"""
    keyboard = [
        [InlineKeyboardButton(
            f"💫 Узнать кто отправил ({REVEAL_PRICE}⭐)",
            callback_data=f"reveal_{valentine_id}"
        )],
        [InlineKeyboardButton("◀️ В меню", callback_data="menu_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = VALENTINE_RECEIVED_TEXT.format(message=message)

    if music_url:
        text += f"\n🎵 Музыка: {music_url}"

    await context.bot.send_message(
        chat_id=recipient_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to edit message"""
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_send")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "✏️ Введи новый текст валентинки:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    return WAITING_MESSAGE


async def cancel_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel sending"""
    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    from handlers.start import show_main_menu
    await show_main_menu(update, context)

    return ConversationHandler.END


def get_send_handlers():
    """Return send-related handlers"""
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_send, pattern="^menu_send$")
        ],
        states={
            WAITING_RECIPIENT: [
                MessageHandler(filters.TEXT | filters.FORWARDED, receive_recipient),
            ],
            WAITING_MESSAGE: [
                CallbackQueryHandler(use_template, pattern="^template_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message),
            ],
            CONFIRM_SEND: [
                CallbackQueryHandler(confirm_send, pattern="^confirm_send$"),
                CallbackQueryHandler(edit_message, pattern="^edit_message$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_send, pattern="^cancel_send$"),
        ],
        per_message=False,
    )

    return [conv_handler]
