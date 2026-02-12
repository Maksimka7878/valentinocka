"""
Compatibility test - two people answer questions and get % match
"""
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes, CallbackQueryHandler

import database as db
from config import COMPAT_PRICE, BOT_USERNAME

# 7 compatibility questions
COMPAT_QUESTIONS = [
    {
        "q": "🌅 Идеальное свидание?",
        "options": ["🏠 Уютный вечер дома", "🍽️ Ресторан", "🎬 Кино", "🌳 Прогулка"]
    },
    {
        "q": "🐾 Кошки или собаки?",
        "options": ["🐱 Кошки", "🐶 Собаки", "🐹 Другие", "🚫 Без питомцев"]
    },
    {
        "q": "🎵 Любимая музыка?",
        "options": ["🎸 Рок", "🎤 Поп", "🎹 Классика", "🎧 Электро/Рэп"]
    },
    {
        "q": "☀️ Утро или вечер?",
        "options": ["🌅 Жаворонок", "🌙 Сова", "🦉 Совсем сова", "🤷 Как получится"]
    },
    {
        "q": "🏖️ Идеальный отпуск?",
        "options": ["🏖️ Пляж", "🏔️ Горы", "🏙️ Город", "🏕️ Кемпинг"]
    },
    {
        "q": "🍕 Любимая еда?",
        "options": ["🍕 Пицца", "🍣 Суши", "🥗 Здоровая", "🍔 Фастфуд"]
    },
    {
        "q": "💝 Что важнее в отношениях?",
        "options": ["🗣️ Общение", "🤗 Объятия", "🎁 Подарки", "✨ Совместные дела"]
    },
]


async def start_compatibility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start compatibility test - show payment"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(
            f"💕 Начать тест ({COMPAT_PRICE}⭐)",
            callback_data="pay_compat"
        )],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu_main")]
    ]

    await query.edit_message_text(
        "💕 **ТЕСТ СОВМЕСТИМОСТИ**\n\n"
        "Узнай, насколько вы подходите друг другу!\n\n"
        "📋 Как это работает:\n"
        "1️⃣ Ты отвечаешь на 7 вопросов\n"
        "2️⃣ Получаешь ссылку для партнёра\n"
        "3️⃣ Партнёр отвечает на те же вопросы\n"
        "4️⃣ Бот считает % совместимости!\n\n"
        f"💰 Стоимость: **{COMPAT_PRICE}⭐**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def pay_compat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create invoice for compatibility test"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    prices = [LabeledPrice(label="Тест совместимости", amount=COMPAT_PRICE)]

    # Create test first
    test_id = await db.create_compat_test(user.id)
    context.user_data['compat_test_id'] = test_id

    await context.bot.send_invoice(
        chat_id=user.id,
        title="Тест совместимости 💕",
        description="Узнай % совместимости с твоей половинкой!",
        payload=f"compat_{test_id}",
        currency="XTR",
        prices=prices,
    )


async def start_compat_questions(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  test_id: str, is_partner: bool = False):
    """Start asking questions"""
    context.user_data['compat_test_id'] = test_id
    context.user_data['compat_answers'] = []
    context.user_data['compat_question'] = 0
    context.user_data['compat_is_partner'] = is_partner

    await ask_compat_question(update, context, 0)


async def ask_compat_question(update: Update, context: ContextTypes.DEFAULT_TYPE, q_index: int):
    """Ask one question"""
    if q_index >= len(COMPAT_QUESTIONS):
        # All questions answered
        await finish_compat(update, context)
        return

    q = COMPAT_QUESTIONS[q_index]

    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"compat_ans_{q_index}_{i}")]
        for i, opt in enumerate(q['options'])
    ]

    text = (
        f"💕 **Вопрос {q_index + 1} из {len(COMPAT_QUESTIONS)}**\n\n"
        f"{q['q']}"
    )

    target = update.callback_query if update.callback_query else None
    if target:
        await target.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.effective_message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


async def handle_compat_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle compatibility answer"""
    query = update.callback_query
    await query.answer()

    parts = query.data.replace("compat_ans_", "").split("_")
    q_index = int(parts[0])
    answer = int(parts[1])

    answers = context.user_data.get('compat_answers', [])
    answers.append(answer)
    context.user_data['compat_answers'] = answers

    # Next question
    await ask_compat_question(update, context, q_index + 1)


async def finish_compat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finish compatibility test"""
    test_id = context.user_data.get('compat_test_id')
    answers = context.user_data.get('compat_answers', [])
    is_partner = context.user_data.get('compat_is_partner', False)
    user = update.effective_user

    # Save answers
    await db.save_compat_answers(test_id, user.id, answers)

    test = await db.get_compat_test(test_id)

    if is_partner and test and test['initiator_answers']:
        # Both answered - calculate result
        initiator_answers = json.loads(test['initiator_answers'])
        matches = sum(1 for a, b in zip(initiator_answers, answers) if a == b)
        percent = int((matches / len(COMPAT_QUESTIONS)) * 100)

        await db.set_compat_result(test_id, percent)

        # Get result text
        result_text = get_compat_result_text(percent)

        # Send to both
        result_msg = (
            f"💕 **РЕЗУЛЬТАТ СОВМЕСТИМОСТИ**\n\n"
            f"{'🔥' * (percent // 20 + 1)}\n\n"
            f"**{percent}%** совместимости!\n\n"
            f"{result_text}"
        )

        keyboard = [[InlineKeyboardButton("◀️ Меню", callback_data="menu_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send to partner (current user)
        if update.callback_query:
            await update.callback_query.edit_message_text(
                result_msg, reply_markup=reply_markup, parse_mode="Markdown"
            )
        else:
            await update.effective_message.reply_text(
                result_msg, reply_markup=reply_markup, parse_mode="Markdown"
            )

        # Send to initiator
        try:
            await context.bot.send_message(
                chat_id=test['initiator_id'],
                text=result_msg,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception:
            pass

    else:
        # Initiator finished - generate link for partner
        link = f"https://t.me/{BOT_USERNAME}?start=compat_{test_id}"

        keyboard = [
            [InlineKeyboardButton("📤 Отправить партнёру",
                url=f"https://t.me/share/url?url={link}&text=Пройди тест совместимости! 💕")],
            [InlineKeyboardButton("◀️ Меню", callback_data="menu_main")]
        ]

        if update.callback_query:
            await update.callback_query.edit_message_text(
                f"✅ **Ответы сохранены!**\n\n"
                f"Теперь отправь ссылку партнёру:\n"
                f"`{link}`\n\n"
                f"Когда партнёр ответит — вы оба получите результат! 💕",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await update.effective_message.reply_text(
                f"✅ **Ответы сохранены!**\n\n"
                f"Теперь отправь ссылку партнёру:\n"
                f"`{link}`\n\n"
                f"Когда партнёр ответит — вы оба получите результат! 💕",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )


def get_compat_result_text(percent: int) -> str:
    """Get result description based on percent"""
    if percent >= 80:
        return "🔥 Вы идеально подходите друг другу! Настоящая пара!"
    elif percent >= 60:
        return "💕 Отличная совместимость! У вас много общего!"
    elif percent >= 40:
        return "💛 Неплохо! Противоположности притягиваются!"
    elif percent >= 20:
        return "🤔 Вы разные, но это может быть интересно!"
    else:
        return "😅 Полные противоположности! Но любовь побеждает всё!"


def get_compat_handlers():
    """Return compatibility handlers"""
    return [
        CallbackQueryHandler(start_compatibility, pattern="^menu_compat$"),
        CallbackQueryHandler(pay_compat, pattern="^pay_compat$"),
        CallbackQueryHandler(handle_compat_answer, pattern="^compat_ans_"),
    ]
