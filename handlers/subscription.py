"""
Subscription management handler
Plans: Romantic (150⭐/mo), Lovebomb (300⭐/mo), Lovebomb 3m (700⭐)
"""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes, CallbackQueryHandler

import database as db
from config import SUB_ROMANTIC_PRICE, SUB_LOVEBOMB_PRICE, SUB_LOVEBOMB_3M_PRICE


PLAN_NAMES = {
    "romantic": "Romantic 💕",
    "lovebomb": "Lovebomb 💣",
}

PLAN_EMOJI = {
    "romantic": "💕",
    "lovebomb": "💣",
}


async def show_subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show subscription plans menu"""
    query = update.callback_query
    if query:
        await query.answer()
    user = query.from_user if query else update.effective_user

    sub = await db.get_active_subscription(user.id)

    if sub:
        expires = sub['expires_at'][:10]
        plan_name = PLAN_NAMES.get(sub['plan'], sub['plan'])
        status_text = (
            f"✅ У тебя активна подписка **{plan_name}**\n"
            f"Действует до: **{expires}**\n\n"
            f"Хочешь продлить или сменить план?"
        )
    else:
        status_text = "⭐ У тебя нет активной подписки.\n\nВыбери план:"

    text = f"""
⭐ **PREMIUM ПОДПИСКА**

{status_text}

━━━━━━━━━━━━━━━━
💕 **Romantic** — {SUB_ROMANTIC_PRICE}⭐/мес
• 10 валентинок в день (вместо 3)
• 1 бесплатное стихотворение в неделю
• Безлимитная рулетка
• Значок Premium 💕

━━━━━━━━━━━━━━━━
💣 **Lovebomb** — {SUB_LOVEBOMB_PRICE}⭐/мес
• Безлимитные валентинки
• Все платные функции БЕСПЛАТНО
• Приоритет в рулетке
• Значок VIP 💣

━━━━━━━━━━━━━━━━
💣 **Lovebomb × 3 мес** — {SUB_LOVEBOMB_3M_PRICE}⭐
• Всё что в Lovebomb
• Скидка 22% (вместо 900⭐ — 700⭐)
"""

    keyboard = [
        [InlineKeyboardButton(
            f"💕 Romantic — {SUB_ROMANTIC_PRICE}⭐/мес",
            callback_data="sub_buy_romantic"
        )],
        [InlineKeyboardButton(
            f"💣 Lovebomb — {SUB_LOVEBOMB_PRICE}⭐/мес",
            callback_data="sub_buy_lovebomb"
        )],
        [InlineKeyboardButton(
            f"💣 Lovebomb × 3 мес — {SUB_LOVEBOMB_3M_PRICE}⭐ (−22%)",
            callback_data="sub_buy_lovebomb3m"
        )],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]
    ]

    if query:
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )


async def buy_romantic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send invoice for Romantic plan"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    await context.bot.send_invoice(
        chat_id=user.id,
        title="Подписка Romantic 💕",
        description="10 валентинок/день · 1 стихотворение/нед · безлимитная рулетка · значок Premium",
        payload=f"sub_romantic_{user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Romantic (1 месяц)", amount=SUB_ROMANTIC_PRICE)],
    )


async def buy_lovebomb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send invoice for Lovebomb monthly plan"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    await context.bot.send_invoice(
        chat_id=user.id,
        title="Подписка Lovebomb 💣",
        description="Безлимит · все функции бесплатно · VIP значок · приоритет в рулетке",
        payload=f"sub_lovebomb_{user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Lovebomb (1 месяц)", amount=SUB_LOVEBOMB_PRICE)],
    )


async def buy_lovebomb3m(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send invoice for Lovebomb 3-month plan"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    await context.bot.send_invoice(
        chat_id=user.id,
        title="Подписка Lovebomb × 3 месяца 💣",
        description="Всё что в Lovebomb · на 3 месяца · скидка 22%",
        payload=f"sub_lovebomb3m_{user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Lovebomb (3 месяца)", amount=SUB_LOVEBOMB_3M_PRICE)],
    )


async def check_sub_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check subscription status (from callback or message)"""
    await show_subscription_menu(update, context)


def get_subscription_handlers():
    """Return subscription-related handlers"""
    return [
        CallbackQueryHandler(show_subscription_menu, pattern="^menu_premium$"),
        CallbackQueryHandler(buy_romantic, pattern="^sub_buy_romantic$"),
        CallbackQueryHandler(buy_lovebomb, pattern="^sub_buy_lovebomb$"),
        CallbackQueryHandler(buy_lovebomb3m, pattern="^sub_buy_lovebomb3m$"),
    ]
