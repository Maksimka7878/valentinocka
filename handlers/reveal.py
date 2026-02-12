"""
Reveal sender handlers with Telegram Stars payment
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes, CallbackQueryHandler

import database as db
from config import REVEAL_PRICE
from templates import REVEAL_PROMPT_TEXT, SENDER_REVEALED_TEXT


async def reveal_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show reveal payment prompt"""
    query = update.callback_query
    await query.answer()

    valentine_id = int(query.data.replace("reveal_", ""))

    # Get valentine
    valentine = await db.get_valentine(valentine_id)

    if not valentine:
        await query.edit_message_text(" Валентинка не найдена.")
        return

    user = query.from_user

    # Check if this is the receiver
    if valentine['receiver_id'] != user.id:
        await query.answer(" Это не твоя валентинка!", show_alert=True)
        return

    # Check if already revealed
    if valentine['is_revealed']:
        sender = await db.get_or_create_user(valentine['sender_id'])
        await query.edit_message_text(
            SENDER_REVEALED_TEXT.format(
                name=sender['first_name'] or "Пользователь",
                username=sender['username'] or "скрыт"
            ),
            parse_mode="Markdown"
        )
        return

    # Show payment prompt
    keyboard = [
        [InlineKeyboardButton(
            f" Заплатить {REVEAL_PRICE}",
            callback_data=f"pay_reveal_{valentine_id}"
        )],
        [InlineKeyboardButton(" Назад", callback_data="menu_inbox")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        REVEAL_PROMPT_TEXT,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def initiate_reveal_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create Stars invoice for reveal"""
    query = update.callback_query
    await query.answer()

    valentine_id = int(query.data.replace("pay_reveal_", ""))

    # Verify valentine exists and belongs to user
    valentine = await db.get_valentine(valentine_id)
    if not valentine or valentine['receiver_id'] != query.from_user.id:
        await query.answer(" Ошибка!", show_alert=True)
        return

    if valentine['is_revealed']:
        await query.answer(" Уже раскрыто!", show_alert=True)
        return

    # Create invoice
    prices = [LabeledPrice(label="Раскрыть отправителя", amount=REVEAL_PRICE)]

    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title="Раскрыть отправителя",
        description="Узнай, кто отправил тебе эту валентинку!",
        payload=f"reveal_{valentine_id}",
        currency="XTR",  # Telegram Stars
        prices=prices,
    )


def get_reveal_handlers():
    """Return reveal-related handlers"""
    return [
        CallbackQueryHandler(reveal_prompt, pattern="^reveal_\\d+$"),
        CallbackQueryHandler(initiate_reveal_payment, pattern="^pay_reveal_\\d+$"),
    ]
