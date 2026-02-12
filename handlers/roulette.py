"""
Love Roulette - Random anonymous valentine exchange
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, filters
)

import database as db
from templates import format_valentine, VALENTINE_RECEIVED_TEXT
from config import ROULETTE_EXTRA_PRICE

WAITING_ROULETTE_MSG = 0


async def start_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start roulette flow — check daily free limit first"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    can_free = await db.can_use_roulette_free(user.id)

    if not can_free and not context.user_data.pop('roulette_paid', False):
        # Limit reached — offer to pay 10⭐
        keyboard = [
            [InlineKeyboardButton(
                f"🎰 Ещё матч ({ROULETTE_EXTRA_PRICE}⭐)",
                callback_data="buy_roulette_extra"
            )],
            [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]
        ]
        await query.edit_message_text(
            "🎰 **LOVE-РУЛЕТКА**\n\n"
            "⚠️ Бесплатный матч на сегодня уже использован!\n\n"
            f"Хочешь ещё один? Всего **{ROULETTE_EXTRA_PRICE}⭐**\n\n"
            "💡 Подписчики Premium получают безлимитную рулетку!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_roulette")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "🎰 **LOVE-РУЛЕТКА**\n\n"
        "Напиши анонимную валентинку — бот найдёт тебе случайного собеседника "
        "и вы обменяетесь посланиями!\n\n"
        "✍️ Напиши текст своей валентинки:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    return WAITING_ROULETTE_MSG


async def receive_roulette_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive roulette message and try to match"""
    user = update.effective_user
    message = update.message.text.strip()

    if len(message) > 500:
        await update.message.reply_text("❌ Слишком длинно! Максимум 500 символов.")
        return WAITING_ROULETTE_MSG

    # Record roulette usage
    await db.use_roulette_slot(user.id)

    # Check for existing match
    match = await db.find_roulette_match(user.id)

    if match:
        # Found a match! Exchange valentines
        await db.mark_roulette_matched(match['id'])

        # Create valentines for both
        v1_id = await db.create_valentine(
            sender_id=user.id,
            receiver_id=match['user_id'],
            message=message
        )
        v2_id = await db.create_valentine(
            sender_id=match['user_id'],
            receiver_id=user.id,
            message=match['message']
        )

        await db.mark_delivered(v1_id)
        await db.mark_delivered(v2_id)

        # Send to current user
        formatted_received = format_valentine(match['message'])
        keyboard1 = [
            [InlineKeyboardButton("💬 Анонимный чат", callback_data=f"anonchat_{v2_id}")],
            [InlineKeyboardButton("🎰 Ещё раз!", callback_data="menu_roulette")],
            [InlineKeyboardButton("◀️ Меню", callback_data="menu_main")]
        ]
        await update.message.reply_text(
            f"🎰 **МАТЧ НАЙДЕН!**\n\n"
            f"Тебе пришла валентинка:\n\n{formatted_received}",
            reply_markup=InlineKeyboardMarkup(keyboard1),
            parse_mode="Markdown"
        )

        # Send to matched user
        formatted_sent = format_valentine(message)
        keyboard2 = [
            [InlineKeyboardButton("💬 Анонимный чат", callback_data=f"anonchat_{v1_id}")],
            [InlineKeyboardButton("🎰 Ещё раз!", callback_data="menu_roulette")],
            [InlineKeyboardButton("◀️ Меню", callback_data="menu_main")]
        ]
        try:
            await context.bot.send_message(
                chat_id=match['user_id'],
                text=f"🎰 **МАТЧ В РУЛЕТКЕ!**\n\n"
                     f"Тебе пришла валентинка:\n\n{formatted_sent}",
                reply_markup=InlineKeyboardMarkup(keyboard2),
                parse_mode="Markdown"
            )
        except Exception:
            pass

        # Check achievements
        from handlers.achievements import check_achievements
        await check_achievements(user.id, 'roulette', context)

    else:
        # No match - add to queue
        await db.add_to_roulette(user.id, message)

        keyboard = [
            [InlineKeyboardButton("◀️ Меню", callback_data="menu_main")]
        ]
        await update.message.reply_text(
            "⏳ **Ожидаем пару...**\n\n"
            "Твоя валентинка в очереди! Как только кто-то присоединится — "
            "вы обменяетесь посланиями.\n\n"
            "Мы уведомим тебя! 🔔",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    return ConversationHandler.END


async def cancel_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel roulette"""
    query = update.callback_query
    await query.answer()

    from handlers.start import show_main_menu
    await show_main_menu(update, context)
    return ConversationHandler.END


def get_roulette_handlers():
    """Return roulette handlers"""
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_roulette, pattern="^menu_roulette$")
        ],
        states={
            WAITING_ROULETTE_MSG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_roulette_message),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_roulette, pattern="^cancel_roulette$"),
        ],
        per_message=False,
    )
    return [conv]
