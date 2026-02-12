"""
Achievements and badges system
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

import database as db

# Badge definitions
BADGES = {
    "first_valentine": {"emoji": "💌", "name": "Первая валентинка", "desc": "Отправил(а) первую валентинку"},
    "serial_romantic": {"emoji": "🔥", "name": "Серийный романтик", "desc": "Отправил(а) 5+ валентинок"},
    "popular": {"emoji": "👑", "name": "Король/Королева", "desc": "Получил(а) 10+ валентинок"},
    "mutual": {"emoji": "💕", "name": "Взаимность", "desc": "Получил(а) валентинку в ответ"},
    "voice_sender": {"emoji": "🎤", "name": "Голосистый(ая)", "desc": "Отправил(а) голосовую валентинку"},
    "roulette_player": {"emoji": "🎰", "name": "Авантюрист", "desc": "Участвовал(а) в рулетке"},
    "photo_sender": {"emoji": "📸", "name": "Фотограф", "desc": "Отправил(а) фото-валентинку"},
    "gift_giver": {"emoji": "🎁", "name": "Щедрый(ая)", "desc": "Прикрепил(а) подарок"},
    "music_lover": {"emoji": "🎵", "name": "Меломан", "desc": "Отправил(а) музыкальную валентинку"},
    "chain_master": {"emoji": "⛓️", "name": "Мастер цепочек", "desc": "Запустил(а) цепочку из 3+ валентинок"},
    "poet": {"emoji": "✍️", "name": "Поэт", "desc": "Заказал(а) AI-стихотворение"},
    "generous": {"emoji": "💎", "name": "Меценат", "desc": "Купил(а) пакет валентинок"},
    "revealer": {"emoji": "🔮", "name": "Любопытный(ая)", "desc": "Раскрыл(а) отправителя"},
    "subscriber": {"emoji": "⭐", "name": "Премиум", "desc": "Оформил(а) Premium подписку"},
}


async def check_achievements(user_id: int, action: str, context: ContextTypes.DEFAULT_TYPE):
    """Check and grant achievements after action"""
    new_badges = []

    if action == 'send':
        # First valentine
        if await db.grant_achievement(user_id, 'first_valentine'):
            new_badges.append('first_valentine')

        # Serial romantic (5+)
        stats = await db.get_user_stats(user_id)
        if stats['sent'] >= 5:
            if await db.grant_achievement(user_id, 'serial_romantic'):
                new_badges.append('serial_romantic')

    elif action == 'receive':
        stats = await db.get_user_stats(user_id)
        if stats['received'] >= 10:
            if await db.grant_achievement(user_id, 'popular'):
                new_badges.append('popular')

    elif action == 'voice':
        if await db.grant_achievement(user_id, 'voice_sender'):
            new_badges.append('voice_sender')

    elif action == 'photo':
        if await db.grant_achievement(user_id, 'photo_sender'):
            new_badges.append('photo_sender')

    elif action == 'roulette':
        if await db.grant_achievement(user_id, 'roulette_player'):
            new_badges.append('roulette_player')

    elif action == 'gift':
        if await db.grant_achievement(user_id, 'gift_giver'):
            new_badges.append('gift_giver')

    elif action == 'music':
        if await db.grant_achievement(user_id, 'music_lover'):
            new_badges.append('music_lover')

    elif action == 'chain':
        if await db.grant_achievement(user_id, 'chain_master'):
            new_badges.append('chain_master')

    elif action == 'poem':
        if await db.grant_achievement(user_id, 'poet'):
            new_badges.append('poet')

    elif action == 'bundle':
        if await db.grant_achievement(user_id, 'generous'):
            new_badges.append('generous')

    elif action == 'reveal':
        if await db.grant_achievement(user_id, 'revealer'):
            new_badges.append('revealer')

    elif action == 'subscriber':
        if await db.grant_achievement(user_id, 'subscriber'):
            new_badges.append('subscriber')

    # Notify about new badges
    for badge_key in new_badges:
        badge = BADGES[badge_key]
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🎖 **Новый бейдж!**\n\n"
                     f"{badge['emoji']} **{badge['name']}**\n"
                     f"{badge['desc']}\n\n"
                     f"Посмотри все бейджи в меню!",
                parse_mode="Markdown"
            )
        except Exception:
            pass


async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's achievements"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_badges = await db.get_user_achievements(user.id)
    earned_keys = {b['badge'] for b in user_badges}

    text = "🏅 **ТВОИ ДОСТИЖЕНИЯ**\n\n"

    for key, badge in BADGES.items():
        if key in earned_keys:
            text += f"✅ {badge['emoji']} **{badge['name']}** — {badge['desc']}\n"
        else:
            text += f"⬜ {badge['emoji']} _{badge['name']}_ — {badge['desc']}\n"

    text += f"\n🎖 Получено: **{len(earned_keys)}** / **{len(BADGES)}**"

    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def get_achievement_handlers():
    """Return achievement handlers"""
    return [
        CallbackQueryHandler(show_achievements, pattern="^menu_achievements$"),
    ]
