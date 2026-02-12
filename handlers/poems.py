"""
Poem generation handlers
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, filters
)

import database as db
from config import POEM_PRICE, OPENAI_API_KEY
from templates import POEM_START_TEXT, get_random_poem

# Conversation states
WAITING_NAME = 0


async def start_poem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start poem generation flow"""
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton(" Отмена", callback_data="cancel_poem")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        POEM_START_TEXT,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    return WAITING_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive name and generate poem"""
    name = update.message.text.strip()

    if len(name) > 50:
        await update.message.reply_text(
            " Имя слишком длинное! Введи короче (до 50 символов)."
        )
        return WAITING_NAME

    # Store name
    context.user_data['poem_name'] = name

    # Generate poem (AI or template)
    if OPENAI_API_KEY:
        poem = await generate_ai_poem(name)
    else:
        poem = get_random_poem(name)

    context.user_data['generated_poem'] = poem

    # Show poem preview and payment button
    keyboard = [
        [InlineKeyboardButton(
            f" Купить стих ({POEM_PRICE})",
            callback_data="pay_poem"
        )],
        [InlineKeyboardButton(" Другой вариант", callback_data="regenerate_poem")],
        [InlineKeyboardButton(" Отмена", callback_data="cancel_poem")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f" **Стихотворение для {name}:**\n\n{poem}\n\n"
        f"Оплати {POEM_PRICE}, чтобы использовать это стихотворение в валентинке!",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    return ConversationHandler.END


async def generate_ai_poem(name: str) -> str:
    """Generate poem using OpenAI API"""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Ты - талантливый русский поэт. Пиши короткие романтичные стихи для валентинок. Стихи должны быть 4-6 строк, с рифмой."
                },
                {
                    "role": "user",
                    "content": f"Напиши короткое романтичное стихотворение-валентинку для человека по имени {name}. Используй имя в стихе."
                }
            ],
            max_tokens=200,
            temperature=0.9
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback to template
        return get_random_poem(name)


async def regenerate_poem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate another poem variant"""
    query = update.callback_query
    await query.answer()

    name = context.user_data.get('poem_name', 'друг')

    # Generate new poem
    if OPENAI_API_KEY:
        poem = await generate_ai_poem(name)
    else:
        poem = get_random_poem(name)

    context.user_data['generated_poem'] = poem

    keyboard = [
        [InlineKeyboardButton(
            f" Купить стих ({POEM_PRICE})",
            callback_data="pay_poem"
        )],
        [InlineKeyboardButton(" Другой вариант", callback_data="regenerate_poem")],
        [InlineKeyboardButton(" Отмена", callback_data="cancel_poem")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f" **Новое стихотворение для {name}:**\n\n{poem}\n\n"
        f"Оплати {POEM_PRICE}, чтобы использовать это стихотворение в валентинке!",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def pay_poem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create invoice for poem"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    prices = [LabeledPrice(label="AI-стихотворение", amount=POEM_PRICE)]

    await context.bot.send_invoice(
        chat_id=user.id,
        title="AI-стихотворение",
        description="Уникальное стихотворение для твоей валентинки!",
        payload=f"poem_{user.id}",
        currency="XTR",
        prices=prices,
    )

    # Store poem for later use (will be available after payment)
    context.user_data['paid_poem'] = context.user_data.get('generated_poem', '')


async def cancel_poem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel poem generation"""
    query = update.callback_query
    await query.answer()

    # Clear poem data
    context.user_data.pop('poem_name', None)
    context.user_data.pop('generated_poem', None)

    from handlers.start import show_main_menu
    await show_main_menu(update, context)

    return ConversationHandler.END


def get_poem_handlers():
    """Return poem-related handlers"""
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_poem, pattern="^menu_poem$")
        ],
        states={
            WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_poem, pattern="^cancel_poem$"),
        ],
        per_message=False,
    )

    return [
        conv_handler,
        CallbackQueryHandler(regenerate_poem, pattern="^regenerate_poem$"),
        CallbackQueryHandler(pay_poem, pattern="^pay_poem$"),
        CallbackQueryHandler(cancel_poem, pattern="^cancel_poem$"),
    ]
