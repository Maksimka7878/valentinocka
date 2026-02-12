"""
Valentine Bot v2.0 - Main entry point
Telegram bot for anonymous valentines with Telegram Stars monetization
"""
import asyncio
import logging

from telegram.ext import Application

import config
import database as db
from handlers import register_all_handlers
from scheduler import run_scheduler

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Initialize database and bot settings after startup"""
    # Initialize database
    await db.init_db()
    logger.info("Database initialized")

    # Get bot info and store username
    bot_info = await application.bot.get_me()
    config.BOT_USERNAME = bot_info.username
    logger.info(f"Bot started: @{config.BOT_USERNAME}")

    # Start scheduler for delayed valentines
    asyncio.create_task(run_scheduler(application.bot))
    logger.info("Scheduler started for delayed deliveries")


def main():
    """Main function to run the bot"""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not set! Please set it in .env file")
        return

    # Create application
    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register all handlers
    register_all_handlers(application)

    # Start polling
    logger.info("Starting Valentine Bot v2.0...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
