"""
Annual occasions handler — use the bot year-round, not just on Valentine's Day.
Occasions: birthday, crush, friendship, march8, feb23, apology, gratitude, santa
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from config import OCCASIONS

# Templates per occasion
OCCASION_TEMPLATES = {
    "birthday": [
        "С днём рождения! 🎂 Ты особенный(ая) человек и заслуживаешь всего лучшего!",
        "Поздравляю с днём рождения! 🥳 Пусть этот год принесёт тебе всё, о чём мечтаешь!",
        "С ДР! 🎉 Ты делаешь жизнь окружающих ярче просто фактом своего существования!",
    ],
    "crush": [
        "Мне сложно сказать это вслух, но ты мне очень нравишься... 💘",
        "Я думаю о тебе каждый день. Не знаю, замечаешь ли ты меня... 🥺",
        "Ты — тот человек, ради которого я невольно улыбаюсь. Без причины. 💕",
    ],
    "friendship": [
        "Ты лучший(ая) друг в мире. Серьёзно. 🤝 Спасибо, что ты есть!",
        "Дружба с тобой — это подарок. Ценю каждый момент с тобой! 🫂",
        "Ты — тот человек, которому я доверяю всё. Спасибо за это. 💙",
    ],
    "march8": [
        "С 8 Марта! 🌷 Ты — настоящая сила природы. Красивая, умная, неповторимая!",
        "Поздравляю с женским днём! 🌸 Ты заслуживаешь только цветов и улыбок каждый день!",
        "С праздником! 🌺 Пусть в твоей жизни будет столько радости, сколько ты даришь другим!",
    ],
    "feb23": [
        "С 23 Февраля! 🎖 Ты — настоящий защитник. Надёжный, сильный, верный!",
        "Поздравляю с Днём защитника! 💪 Ты — тот, на кого всегда можно положиться!",
        "С праздником! 🎖 Спасибо, что ты такой человек — сильный духом и добрый сердцем!",
    ],
    "apology": [
        "Мне жаль. Я был(а) неправ(а) и хочу это исправить. Прости меня... 🙏",
        "Извини. Я понимаю, что обидел(а) тебя. Ты важен(а) для меня. 💔",
        "Прости, пожалуйста. Мои слова/поступки были неправильными. Хочу исправить это. 🙏",
    ],
    "gratitude": [
        "Спасибо за всё, что ты делаешь. Ты не представляешь, как это важно для меня! 🌟",
        "Хочу сказать тебе спасибо. За поддержку, за доброту, за то, что ты просто есть. ✨",
        "Ты делаешь мир лучше. Серьёзно. Спасибо, что ты такой(ая)! 💫",
    ],
    "santa": [
        "Привет от Тайного Санты! 🎅 Я слежу за тобой весь год — и ты был(а) очень хорошим(ей)!",
        "Тайный Санта хочет сказать: ты заслуживаешь самых лучших подарков! 🎁",
        "От твоего Тайного Санты с любовью! 🎄 Пусть твои желания исполнятся!",
    ],
}

OCCASION_INTRO = {
    "birthday": "🎂 Отправь анонимное поздравление с Днём рождения!",
    "crush": "💘 Признайся в симпатии анонимно — пусть узнает о твоих чувствах!",
    "friendship": "🤝 Скажи другу что-то важное анонимно — иногда так честнее!",
    "march8": "🌷 Поздравь с 8 Марта анонимно — пусть почувствует себя особенной!",
    "feb23": "🎖 Поздравь с 23 Февраля анонимно!",
    "apology": "🙏 Извинись анонимно — иногда слова проще написать, чем сказать вслух.",
    "gratitude": "🌟 Поблагодари анонимно — пусть знает, как ты ценишь его/её!",
    "santa": "🎅 Отправь послание как Тайный Санта!",
}


async def show_occasions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show occasions menu"""
    query = update.callback_query
    if query:
        await query.answer()

    text = "🎉 **ПОВОДЫ**\n\nВыбери повод — и отправь анонимное послание:"

    keyboard = []
    for key, label in OCCASIONS.items():
        keyboard.append([InlineKeyboardButton(label, callback_data=f"occasion_{key}")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="menu_main")])

    if query:
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )


async def show_occasion_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show templates for a selected occasion"""
    query = update.callback_query
    await query.answer()

    occasion_key = query.data.replace("occasion_", "")
    templates = OCCASION_TEMPLATES.get(occasion_key, [])
    intro = OCCASION_INTRO.get(occasion_key, "Выбери шаблон:")
    occasion_label = OCCASIONS.get(occasion_key, "Повод")

    context.user_data['occasion_key'] = occasion_key

    text = f"**{occasion_label}**\n\n{intro}\n\nВыбери шаблон или напиши своё:"

    keyboard = []
    for i, tmpl in enumerate(templates):
        # Truncate label for button
        short = tmpl[:35] + "..." if len(tmpl) > 35 else tmpl
        keyboard.append([InlineKeyboardButton(
            f"💬 {short}", callback_data=f"occ_tmpl_{occasion_key}_{i}"
        )])

    keyboard.append([InlineKeyboardButton(
        "✍️ Написать своё", callback_data=f"occ_custom_{occasion_key}"
    )])
    keyboard.append([InlineKeyboardButton("◀️ Поводы", callback_data="menu_occasions")])

    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def select_occasion_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selected a template — pre-fill and go to send flow"""
    query = update.callback_query
    await query.answer()

    # occ_tmpl_{key}_{index}
    parts = query.data.replace("occ_tmpl_", "").rsplit("_", 1)
    occasion_key = parts[0]
    idx = int(parts[1])

    templates = OCCASION_TEMPLATES.get(occasion_key, [])
    if idx < len(templates):
        message = templates[idx]
    else:
        message = templates[0]

    context.user_data['valentine_message'] = message
    context.user_data['occasion_key'] = occasion_key

    # Redirect to recipient input (reuse send flow)
    from handlers.send import WAITING_RECIPIENT
    from config import BOT_USERNAME

    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_send")]]
    await query.edit_message_text(
        f"✅ Шаблон выбран:\n\n_{message}_\n\n"
        "💌 **Кому отправить?**\n\nВведи @username получателя:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    context.user_data['from_occasion'] = True
    return WAITING_RECIPIENT


async def occasion_custom_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User wants to write custom occasion message"""
    query = update.callback_query
    await query.answer()

    occasion_key = query.data.replace("occ_custom_", "")
    occasion_label = OCCASIONS.get(occasion_key, "Повод")

    context.user_data['occasion_key'] = occasion_key
    context.user_data['from_occasion'] = True

    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_send")]]
    await query.edit_message_text(
        f"✍️ **{occasion_label}**\n\n"
        "Введи текст послания (до 500 символов):",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    from handlers.send import WAITING_RECIPIENT
    return WAITING_RECIPIENT


def get_occasion_handlers():
    """Return occasion-related handlers"""
    return [
        CallbackQueryHandler(show_occasions_menu, pattern="^menu_occasions$"),
        CallbackQueryHandler(show_occasion_templates, pattern="^occasion_"),
        CallbackQueryHandler(select_occasion_template, pattern="^occ_tmpl_"),
        CallbackQueryHandler(occasion_custom_message, pattern="^occ_custom_"),
    ]
