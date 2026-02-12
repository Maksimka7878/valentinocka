"""
Vercel Serverless Webhook Endpoint for Valentine Bot
Handles incoming Telegram updates via webhook (POST)
Sets up webhook on GET request
"""
import json
import asyncio
import logging
from http.server import BaseHTTPRequestHandler

from telegram import Update, Bot
from telegram.ext import Application

import config
import database as db
from handlers import register_all_handlers

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Global application instance (reused across warm invocations)
_app = None


async def _get_app() -> Application:
    """Get or create the Application instance"""
    global _app
    if _app is None:
        # Initialize database tables
        await db.init_db()

        # Build application
        _app = (
            Application.builder()
            .token(config.BOT_TOKEN)
            .updater(None)  # No updater needed for webhook mode
            .build()
        )

        # Register all handlers
        register_all_handlers(_app)

        # Initialize the application
        await _app.initialize()

        # Get bot info
        bot_info = await _app.bot.get_me()
        config.BOT_USERNAME = bot_info.username
        logger.info(f"Bot initialized: @{config.BOT_USERNAME}")

    return _app


async def _setup_webhook():
    """Set the Telegram webhook URL"""
    bot = Bot(token=config.BOT_TOKEN)

    # Determine webhook URL
    webhook_url = config.WEBHOOK_URL
    if not webhook_url and config.VERCEL_URL:
        webhook_url = f"https://{config.VERCEL_URL}/api/webhook"

    if not webhook_url:
        return {"error": "WEBHOOK_URL or VERCEL_URL not set"}

    await bot.set_webhook(url=webhook_url)
    info = await bot.get_webhook_info()
    return {
        "ok": True,
        "webhook_url": info.url,
        "pending_update_count": info.pending_update_count,
    }


async def _process_update(body: bytes):
    """Process a single Telegram update"""
    app = await _get_app()
    update = Update.de_json(json.loads(body), app.bot)
    await app.process_update(update)


class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler"""

    def do_GET(self):
        """GET /api/webhook — setup webhook"""
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(_setup_webhook())
            loop.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            logger.error(f"Webhook setup error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_POST(self):
        """POST /api/webhook — process Telegram update"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            loop = asyncio.new_event_loop()
            loop.run_until_complete(_process_update(body))
            loop.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
        except Exception as e:
            logger.error(f"Update processing error: {e}")
            self.send_response(200)  # Always return 200 to Telegram
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "error": str(e)}).encode())
