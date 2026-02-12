"""
Scheduled valentine delivery
"""
import asyncio
import logging
from datetime import datetime

import database as db
from templates import format_valentine, VALENTINE_RECEIVED_TEXT

logger = logging.getLogger(__name__)


async def deliver_scheduled(bot):
    """Check and deliver scheduled valentines"""
    pending = await db.get_pending_scheduled()

    for valentine in pending:
        try:
            message = valentine['message']
            formatted = format_valentine(message, is_premium=valentine.get('is_premium', False))

            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            keyboard = [
                [InlineKeyboardButton(
                    "💫 Узнать кто отправил (50⭐)",
                    callback_data=f"reveal_{valentine['id']}"
                )],
                [InlineKeyboardButton("◀️ В меню", callback_data="menu_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            text = VALENTINE_RECEIVED_TEXT.format(message=formatted)

            # Add gift if present
            if valentine.get('gift_emoji'):
                text = f"🎁 Подарок: {valentine['gift_emoji']}\n\n" + text

            # Send text valentine
            await bot.send_message(
                chat_id=valentine['receiver_id'],
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

            # Send voice if present
            if valentine.get('voice_file_id'):
                await bot.send_voice(
                    chat_id=valentine['receiver_id'],
                    voice=valentine['voice_file_id'],
                    caption="🎤 Голосовая валентинка от тайного поклонника!"
                )

            # Send photo if present
            if valentine.get('photo_file_id'):
                await bot.send_photo(
                    chat_id=valentine['receiver_id'],
                    photo=valentine['photo_file_id'],
                    caption="📸 Фото-валентинка от тайного поклонника!"
                )

            # Mark as sent
            await db.mark_scheduled_sent(valentine['id'])
            logger.info(f"Delivered scheduled valentine {valentine['id']}")

            # Notify sender
            try:
                await bot.send_message(
                    chat_id=valentine['sender_id'],
                    text="✅ Твоя отложенная валентинка доставлена! 💌"
                )
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Failed to deliver scheduled valentine {valentine['id']}: {e}")


async def run_scheduler(bot):
    """Run scheduler loop - check every 30 seconds"""
    logger.info("Scheduler started")
    while True:
        try:
            await deliver_scheduled(bot)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(30)
