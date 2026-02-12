"""
Start command and main menu handlers v2.0
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

import database as db
from templates import WELCOME_TEXT, STATS_TEXT
from config import ZODIAC_SIGNS, CHAIN_TARGET, BOT_USERNAME

# ==================== PERSISTENT REPLY KEYBOARD ====================

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["💌 Отправить послание", "📬 Входящие"],
        ["🎉 Поводы", "🎰 Рулетка"],
        ["💕 Совместимость", "🔮 Гороскоп"],
        ["✍️ Стихи", "⭐ Premium"],
        ["🏆 Топ", "📊 Статистика"],
        ["⛓️ Цепочка", "🎁 Пригласить"],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери действие... 💌",
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command and deep links"""
    user = update.effective_user

    # Register/update user in database
    await db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )

    # Check for deep link
    if context.args:
        arg = context.args[0]
        if arg.startswith("valentine_"):
            valentine_id = int(arg.replace("valentine_", ""))
            await deliver_valentine_by_link(update, context, valentine_id)
            return
        elif arg.startswith("ref_"):
            referrer_id = int(arg.replace("ref_", ""))
            if referrer_id != user.id:
                await db.add_bonus_valentines(referrer_id, 1)
                try:
                    await context.bot.send_message(
                        referrer_id,
                        f"🎁 Твой друг {user.first_name} присоединился! +1 валентинка!"
                    )
                except Exception:
                    pass
        elif arg.startswith("compat_"):
            test_id = arg.replace("compat_", "")
            from handlers.compatibility import start_compat_questions
            await start_compat_questions(update, context, test_id, is_partner=True)
            return

    # Show main menu with reply keyboard
    await show_main_menu(update, context)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu command"""
    await show_main_menu(update, context)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu with inline keyboard"""
    user = update.effective_user

    keyboard = [
        [InlineKeyboardButton("💌 ОТПРАВИТЬ ПОСЛАНИЕ 💌", callback_data="menu_send")],
        [
            InlineKeyboardButton("🎉 Поводы", callback_data="menu_occasions"),
            InlineKeyboardButton("⭐ Premium", callback_data="menu_premium"),
        ],
        [
            InlineKeyboardButton("🎁 Недельный бандл", callback_data="buy_weekbundle"),
        ],
        [
            InlineKeyboardButton("🎤 Голосовая", callback_data="menu_voice"),
            InlineKeyboardButton("📸 Фото", callback_data="menu_photo"),
        ],
        [
            InlineKeyboardButton("📬 Входящие", callback_data="menu_inbox"),
            InlineKeyboardButton("✍️ Стихи", callback_data="menu_poem"),
        ],
        [
            InlineKeyboardButton("🎰 Рулетка", callback_data="menu_roulette"),
            InlineKeyboardButton("💕 Совместимость", callback_data="menu_compat"),
        ],
        [
            InlineKeyboardButton("🔮 Гороскоп", callback_data="menu_horoscope"),
            InlineKeyboardButton("🏅 Бейджи", callback_data="menu_achievements"),
        ],
        [
            InlineKeyboardButton("🏆 Топ", callback_data="menu_top"),
            InlineKeyboardButton("📊 Стата", callback_data="menu_stats"),
            InlineKeyboardButton("🎁 Друзья", callback_data="menu_invite"),
        ],
        [
            InlineKeyboardButton("⛓️ Цепочка", callback_data="menu_chain"),
            InlineKeyboardButton("⏰ Отложить", callback_data="menu_schedule"),
        ],
        [InlineKeyboardButton("❓ Как это работает?", callback_data="menu_help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = WELCOME_TEXT.format(name=user.first_name or "друг")

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        # Single message: welcome text + persistent reply keyboard at bottom
        await update.message.reply_text(
            text=text,
            reply_markup=MAIN_KEYBOARD,
            parse_mode="Markdown"
        )


async def deliver_valentine_by_link(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    valentine_id: int):
    """Deliver valentine when user comes via deep link"""
    from templates import VALENTINE_RECEIVED_TEXT

    valentine = await db.get_valentine(valentine_id)

    if not valentine:
        await update.message.reply_text("❌ Валентинка не найдена.")
        await show_main_menu(update, context)
        return

    user = update.effective_user

    if valentine['receiver_id'] and valentine['receiver_id'] != user.id:
        await update.message.reply_text("❌ Эта валентинка предназначена другому человеку!")
        await show_main_menu(update, context)
        return

    if valentine['is_delivered']:
        await update.message.reply_text("✅ Ты уже получил(а) эту валентинку! Проверь входящие.")
        await show_main_menu(update, context)
        return

    # Mark as delivered
    await db.mark_delivered(valentine_id)

    # Show valentine
    keyboard = [
        [InlineKeyboardButton(
            "💫 Узнать кто отправил (50⭐)",
            callback_data=f"reveal_{valentine_id}"
        )],
        [InlineKeyboardButton("◀️ В меню", callback_data="menu_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = VALENTINE_RECEIVED_TEXT.format(message=valentine['message'])

    if valentine.get('gift_emoji'):
        text = f"🎁 Подарок: {valentine['gift_emoji']}\n\n" + text

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    if valentine.get('voice_file_id'):
        await update.message.reply_voice(
            voice=valentine['voice_file_id'],
            caption="🎤 Голосовая валентинка!"
        )

    if valentine.get('photo_file_id'):
        await update.message.reply_photo(
            photo=valentine['photo_file_id'],
            caption="📸 Фото-валентинка!"
        )

    from handlers.achievements import check_achievements
    await check_achievements(user.id, 'receive', context)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu button callbacks"""
    query = update.callback_query
    await query.answer()

    if query.data == "menu_main":
        await show_main_menu(update, context)
    elif query.data == "menu_stats":
        await show_stats(update, context)
    elif query.data == "menu_invite":
        await show_invite(update, context)
    elif query.data == "menu_help":
        await show_help(update, context)


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show how it works"""
    query = update.callback_query

    text = """
❓ **КАК ЭТО РАБОТАЕТ?**

1️⃣ Ты отправляешь анонимное послание
2️⃣ Получатель видит текст, но НЕ видит от кого
3️⃣ Если хочет узнать — платит 50⭐
4️⃣ Ты получаешь уведомление!

💡 **ВСЕ ВОЗМОЖНОСТИ:**

💌 Текстовое послание — бесплатно (3/день)
🎉 Любой повод: ДР, симпатия, дружба, 8 Марта...
🎤 Голосовое · 📸 Фото-послание
🎰 Love-рулетка — 1 бесплатный матч/день
💕 Тест совместимости с партнёром
🔮 Любовный гороскоп · ✍️ AI-стихи
🎁 Виртуальные подарки · ⏰ Отложенная доставка
⛓️ Цепочка = бонусы · 🏅 Достижения
🎁 Недельный бандл — 20 посланий + рулетка на 7 дней

⭐ **PREMIUM ПОДПИСКА:**
💕 Romantic (150⭐/мес) — 10 посланий/день + 1 стих/нед
💣 Lovebomb (300⭐/мес) — безлимит + все функции бесплатно
"""

    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def show_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show invite link"""
    query = update.callback_query
    from config import BOT_USERNAME

    user_id = query.from_user.id if query else update.effective_user.id
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

    text = f"""🎁 **Пригласи друзей!**

Отправь эту ссылку друзьям:
`{link}`

За каждого приглашённого друга ты получишь **+1 бесплатную валентинку**!

📤 Поделись в соцсетях и получай бонусы!"""

    keyboard = [
        [InlineKeyboardButton("📤 Поделиться", url=f"https://t.me/share/url?url={link}&text=Отправь мне анонимную валентинку! 💌")],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]
    ]

    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    query = update.callback_query
    user = query.from_user if query else update.effective_user

    stats = await db.get_user_stats(user.id)

    sub = await db.get_active_subscription(user.id)
    if sub:
        plan_labels = {"romantic": "Romantic 💕", "lovebomb": "Lovebomb 💣"}
        plan_label = plan_labels.get(sub['plan'], sub['plan'])
        expires = sub['expires_at'][:10]
        stats['subscription'] = f"{plan_label} (до {expires})"
    else:
        stats['subscription'] = "Нет (купить ⭐)"

    keyboard = [
        [InlineKeyboardButton("⭐ Купить Premium", callback_data="menu_premium")],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(
            STATS_TEXT.format(**stats),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            STATS_TEXT.format(**stats),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


async def end_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End anonymous chat"""
    if 'anon_chat' in context.user_data:
        context.user_data.pop('anon_chat', None)
        context.user_data.pop('anon_role', None)
        context.user_data.pop('anon_valentine', None)
        await update.message.reply_text("💬 Анонимный чат завершён.")
    await show_main_menu(update, context)


# ==================== KEYBOARD BUTTON ROUTER ====================

# Map reply keyboard button text to action
KEYBOARD_BUTTON_MAP = {
    "💌 Отправить послание": "send",
    "📬 Входящие": "inbox",
    "🎉 Поводы": "occasions",
    "🎰 Рулетка": "roulette",
    "💕 Совместимость": "compat",
    "🔮 Гороскоп": "horoscope",
    "✍️ Стихи": "poem",
    "⭐ Premium": "premium",
    "🏆 Топ": "top",
    "📊 Статистика": "stats",
    "⛓️ Цепочка": "chain",
    "🎁 Пригласить": "invite",
}


async def handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route reply keyboard button presses"""
    text = update.message.text
    action = KEYBOARD_BUTTON_MAP.get(text)

    if not action:
        return  # Not a keyboard button, ignore

    user = update.effective_user

    if action == "inbox":
        from handlers.inbox import show_inbox
        await show_inbox(update, context, page=1)

    elif action == "stats":
        await show_stats(update, context)

    elif action == "invite":
        await show_invite(update, context)

    elif action == "top":
        top_receivers = await db.get_top_receivers(5)
        top_senders = await db.get_top_senders(5)

        content = "🏆 **ТОП ВАЛЕНТИНОК**\n\n"
        content += "💌 **Больше всего получили:**\n"
        for i, u in enumerate(top_receivers, 1):
            name = u['first_name'] or u['username'] or 'Аноним'
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i}."
            content += f"{medal} {name} — {u['count']} 💌\n"
        if not top_receivers:
            content += "_Пока нет данных_\n"

        content += "\n💝 **Больше всего отправили:**\n"
        for i, u in enumerate(top_senders, 1):
            name = u['first_name'] or u['username'] or 'Аноним'
            medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i}."
            content += f"{medal} {name} — {u['count']} 💝\n"
        if not top_senders:
            content += "_Пока нет данных. Будь первым! 🚀_\n"

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]]
        await update.message.reply_text(content, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif action == "chain":
        stats = await db.get_user_stats(user.id)
        chain = stats.get('chain', 0)
        progress = min(chain, CHAIN_TARGET)
        bar = "🟥" * progress + "⬜" * (CHAIN_TARGET - progress)

        content = (
            "⛓️ **ЦЕПОЧКА ВАЛЕНТИНОК**\n\n"
            f"Отправь {CHAIN_TARGET} валентинок друзьям — получи\n"
            f"🎁 **1 бесплатную премиум-валентинку!**\n\n"
            f"Прогресс: {bar} ({progress}/{CHAIN_TARGET})\n\n"
        )
        if chain >= CHAIN_TARGET:
            content += "✅ **Цепочка завершена!** Ты получил(а) бонус! 🎉"
        else:
            content += f"Осталось: **{CHAIN_TARGET - progress}** валентинок"

        keyboard = [
            [InlineKeyboardButton("💌 Отправить валентинку", callback_data="menu_send")],
            [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]
        ]
        await update.message.reply_text(content, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif action == "horoscope":
        signs = list(ZODIAC_SIGNS.items())
        keyboard = []
        for i in range(0, len(signs), 4):
            row = [
                InlineKeyboardButton(f"{emoji} {name}", callback_data=f"zodiac_{emoji}")
                for emoji, name in signs[i:i + 4]
            ]
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="menu_main")])
        await update.message.reply_text(
            "🔮 **ЛЮБОВНЫЙ ГОРОСКОП**\n\nВыбери свой знак зодиака:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif action == "compat":
        keyboard = [
            [InlineKeyboardButton("💕 Создать тест совместимости", callback_data="menu_compat")],
            [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]
        ]
        await update.message.reply_text(
            "💕 **ТЕСТ СОВМЕСТИМОСТИ**\n\n"
            "Создай тест и отправь ссылку партнёру — узнайте насколько вы совместимы!\n\n"
            "Нажми кнопку, чтобы начать:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif action == "occasions":
        from handlers.occasions import show_occasions_menu
        await show_occasions_menu(update, context)

    elif action == "premium":
        from handlers.subscription import show_subscription_menu
        await show_subscription_menu(update, context)

    elif action in ("send", "roulette", "poem"):
        route_map = {
            "send": ("menu_send", "💌 Отправить послание"),
            "roulette": ("menu_roulette", "🎰 Участвовать в рулетке"),
            "poem": ("menu_poem", "✍️ Заказать стихотворение"),
        }
        cb_data, btn_text = route_map[action]
        keyboard = [
            [InlineKeyboardButton(btn_text, callback_data=cb_data)],
            [InlineKeyboardButton("◀️ В меню", callback_data="menu_main")]
        ]
        labels = {
            "send": "💌 **ОТПРАВИТЬ ПОСЛАНИЕ**\n\nНажми кнопку ниже, чтобы начать:",
            "roulette": "🎰 **LOVE-РУЛЕТКА**\n\nНажми кнопку, чтобы участвовать:",
            "poem": "✍️ **СТИХИ**\n\nНажми кнопку, чтобы заказать стихотворение:",
        }
        await update.message.reply_text(
            labels[action],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


def get_start_handlers():
    """Return list of start-related handlers"""
    keyboard_filter = filters.TEXT & filters.Regex(
        "^(" + "|".join(k.replace("(", r"\(").replace(")", r"\)") for k in KEYBOARD_BUTTON_MAP.keys()) + ")$"
    )
    return [
        CommandHandler("start", start_command),
        CommandHandler("menu", menu_command),
        CommandHandler("endchat", end_chat_command),
        CallbackQueryHandler(menu_callback, pattern="^menu_(main|stats|invite|help)$"),
        MessageHandler(keyboard_filter & ~filters.COMMAND, handle_keyboard_button),
    ]
