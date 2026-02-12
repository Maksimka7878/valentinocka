"""
Configuration for Valentine Bot v2.0
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Bot token from @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# OpenAI API key for poem generation (optional)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Database — Vercel Postgres
POSTGRES_URL = os.getenv("POSTGRES_URL", "")

# Legacy local SQLite fallback (for local dev without Postgres)
DATABASE_PATH = os.getenv("DATABASE_PATH", "valentine_bot.db")

# Webhook
VERCEL_URL = os.getenv("VERCEL_URL", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Cron secret (to protect cron endpoint)
CRON_SECRET = os.getenv("CRON_SECRET", "")

# ====== Prices in Telegram Stars ======
# Base features
REVEAL_PRICE = 50      # Reveal sender identity
POEM_PRICE = 30        # AI-generated poem
PREMIUM_PRICE = 50     # Premium valentine design
BUNDLE_PRICE = 100     # Pack of 5 valentines

# New v2.0 features
VOICE_PRICE = 30           # Voice valentine
COMPAT_PRICE = 50          # Compatibility test
SCHEDULE_PRICE = 30        # Scheduled delivery
GIFT_PRICE = 20            # Virtual gift
HOROSCOPE_PRICE = 20       # Detailed horoscope
PHOTO_PREMIUM_PRICE = 50   # Premium photo valentine

# ====== Subscriptions ======
SUB_ROMANTIC_PRICE = 150   # Romantic plan - 1 month (10 valentines/day + 1 poem/week)
SUB_LOVEBOMB_PRICE = 300   # Lovebomb plan - 1 month (unlimited + all features free)
SUB_LOVEBOMB_3M_PRICE = 700  # Lovebomb plan - 3 months (save 22%)

# ====== Bundles ======
WEEKLY_BUNDLE_PRICE = 120  # All features bundle: 20 valentines + 7 days free roulette

# ====== Roulette ======
ROULETTE_EXTRA_PRICE = 10  # Extra roulette match after free daily one
ROULETTE_FREE_DAILY = 1    # Free roulette matches per day

# ====== Limits ======
FREE_DAILY_LIMIT = 3       # Free valentines per day (was 1, increased for virality)
ROMANTIC_DAILY_LIMIT = 10  # Romantic subscribers daily limit
MAX_MESSAGE_LENGTH = 500   # Max valentine text length
CHAIN_TARGET = 3           # Send N valentines to unlock VIP
ROULETTE_POOL_SIZE = 2     # Min users for roulette match

# ====== Occasions ======
OCCASIONS = {
    "birthday": "🎂 День рождения",
    "crush": "💘 Симпатия",
    "friendship": "🤝 Дружба",
    "march8": "🌷 8 Марта",
    "feb23": "🎖 23 Февраля",
    "apology": "🙏 Извинение",
    "gratitude": "🌟 Благодарность",
    "santa": "🎅 Тайный Санта",
}

# ====== Virtual Gifts ======
VIRTUAL_GIFTS = {
    "🧸": "Мишка",
    "🌹": "Роза",
    "🍫": "Шоколад",
    "💎": "Бриллиант",
    "🎵": "Мелодия",
    "🎀": "Бантик",
    "🦋": "Бабочка",
    "🌺": "Цветок",
}

# ====== Zodiac Signs ======
ZODIAC_SIGNS = {
    "♈": "Овен",
    "♉": "Телец",
    "♊": "Близнецы",
    "♋": "Рак",
    "♌": "Лев",
    "♍": "Дева",
    "♎": "Весы",
    "♏": "Скорпион",
    "♐": "Стрелец",
    "♑": "Козерог",
    "♒": "Водолей",
    "♓": "Рыбы",
}

# Bot info (will be updated on startup)
BOT_USERNAME = ""
