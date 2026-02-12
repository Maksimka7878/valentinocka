"""
Vercel Cron Endpoint — delivers scheduled valentines
Called periodically by Vercel Cron Jobs
"""
import json
import asyncio
import logging
from http.server import BaseHTTPRequestHandler

from telegram import Bot

import config
import database as db
from scheduler import deliver_scheduled

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def _run_cron():
    """Run scheduled valentine delivery"""
    await db.init_db()
    bot = Bot(token=config.BOT_TOKEN)
    await deliver_scheduled(bot)
    return {"ok": True, "message": "Cron job completed"}


class handler(BaseHTTPRequestHandler):
    """Vercel cron handler"""

    def do_GET(self):
        """GET /api/cron — deliver scheduled valentines"""
        # Security check
        auth = self.headers.get("Authorization", "")
        user_agent = self.headers.get("User-Agent", "")
        
        # Allow if:
        # 1. User-Agent contains vercel-cron (internal Vercel scheduler)
        # 2. Authorization header matches CRON_SECRET
        # 3. CRON_SECRET is not set (insecure mode)
        is_vercel_cron = "vercel-cron" in (user_agent or "")
        is_valid_token = config.CRON_SECRET and auth == f"Bearer {config.CRON_SECRET}"
        is_insecure = not config.CRON_SECRET

        if not (is_vercel_cron or is_valid_token or is_insecure):
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Unauthorized"}).encode())
            return

        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(_run_cron())
            loop.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            logger.error(f"Cron error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
