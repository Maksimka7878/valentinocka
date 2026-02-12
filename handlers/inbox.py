"""
Inbox handlers for viewing received valentines v2.0
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

import database as db
from templates import VALENTINE_DISPLAY

ITEMS_PER_PAGE = 5


async def show_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    """Show user's inbox with pagination"""
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user

    # Get total count
    total = await db.get_inbox_count(user.id)

    if total == 0:
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = "📬 **Твой ящик пуст!**\n\nТебе ещё не прислали валентинок.\nПоделись ссылкой с друзьями! 💌"

        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        return

    # Pagination
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = max(1, min(page, total_pages))
    offset = (page - 1) * ITEMS_PER_PAGE

    valentines = await db.get_inbox(user.id, limit=ITEMS_PER_PAGE, offset=offset)

    text = f"📬 **Входящие** ({total} шт., стр. {page}/{total_pages})\n"

    for v in valentines:
        if v['is_revealed']:
            sender_info = f"💝 Отправитель: **{v['sender_first_name']}** (@{v['sender_username']})"
        else:
            sender_info = "❓ Тайный отправитель"

        created_at = v['created_at'][:10] if v['created_at'] else ""

        text += VALENTINE_DISPLAY.format(
            id=v['id'],
            date=created_at,
            message=v['message'],
            sender_info=sender_info
        )

        # Show media indicators
        extras = []
        if v.get('voice_file_id'):
            extras.append("🎤 Голосовая")
        if v.get('photo_file_id'):
            extras.append("📸 Фото")
        if v.get('gift_emoji'):
            extras.append(f"🎁 Подарок: {v['gift_emoji']}")
        if v.get('music_url'):
            extras.append(f"🎵 Музыка")
        if v.get('reaction'):
            extras.append(f"Реакция: {v['reaction']}")

        if extras:
            text += " | ".join(extras) + "\n"

    # Build keyboard
    keyboard = []

    for v in valentines:
        row = []
        if not v['is_revealed']:
            row.append(InlineKeyboardButton(f"🔮 #{v['id']}", callback_data=f"reveal_{v['id']}"))
        row.append(InlineKeyboardButton(f"💬 Чат", callback_data=f"anonchat_{v['id']}"))
        row.append(InlineKeyboardButton(f"❤️", callback_data=f"react_{v['id']}"))
        if not v.get('gift_emoji'):
            row.append(InlineKeyboardButton(f"🎁", callback_data=f"gift_pick_{v['id']}"))
        keyboard.append(row)

    # Pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"inbox_page_{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"inbox_page_{page + 1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="menu_main")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def inbox_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inbox navigation"""
    query = update.callback_query

    if query.data == "menu_inbox":
        await show_inbox(update, context, page=1)
    elif query.data.startswith("inbox_page_"):
        page = int(query.data.replace("inbox_page_", ""))
        await show_inbox(update, context, page=page)


def get_inbox_handlers():
    """Return inbox-related handlers"""
    return [
        CallbackQueryHandler(inbox_callback, pattern="^menu_inbox$"),
        CallbackQueryHandler(inbox_callback, pattern="^inbox_page_"),
    ]
