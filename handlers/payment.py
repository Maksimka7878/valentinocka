"""
Telegram Stars payment handlers v2.0
"""
from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes, PreCheckoutQueryHandler, MessageHandler, filters, CallbackQueryHandler

import database as db
from config import (
    REVEAL_PRICE, POEM_PRICE, PREMIUM_PRICE, BUNDLE_PRICE,
    VOICE_PRICE, COMPAT_PRICE, SCHEDULE_PRICE, GIFT_PRICE, HOROSCOPE_PRICE,
    SUB_ROMANTIC_PRICE, SUB_LOVEBOMB_PRICE, SUB_LOVEBOMB_3M_PRICE,
    WEEKLY_BUNDLE_PRICE, ROULETTE_EXTRA_PRICE
)
from templates import PAYMENT_SUCCESS_TEXT, SENDER_REVEALED_TEXT


async def pre_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout query - verify payment before processing"""
    query = update.pre_checkout_query
    payload = query.invoice_payload

    parts = payload.split("_")
    payment_type = parts[0]

    valid = False

    if payment_type == "reveal" and len(parts) == 2:
        valentine_id = int(parts[1])
        valentine = await db.get_valentine(valentine_id)

        if valentine and not valentine['is_revealed']:
            valid = True
        else:
            await query.answer(
                ok=False,
                error_message="Валентинка уже раскрыта или не найдена!"
            )
            return

    elif payment_type in ("poem", "bundle", "premium", "compat",
                          "voice", "schedule", "horoscope",
                          "sub", "weekbundle", "roulette"):
        valid = True

    elif payment_type == "gift":
        valid = True

    if valid:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Ошибка платежа. Попробуйте снова.")


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment"""
    payment = update.message.successful_payment
    user = update.effective_user

    payload = payment.invoice_payload
    amount = payment.total_amount
    charge_id = payment.telegram_payment_charge_id

    parts = payload.split("_")
    payment_type = parts[0]

    # Record payment
    valentine_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

    await db.record_payment(
        user_id=user.id,
        amount=amount,
        payment_type=payment_type,
        valentine_id=valentine_id,
        charge_id=charge_id
    )

    # Check achievements
    from handlers.achievements import check_achievements

    # Process based on payment type
    if payment_type == "reveal":
        await process_reveal_payment(update, context, valentine_id)
        await check_achievements(user.id, 'reveal', context)

    elif payment_type == "poem":
        await update.message.reply_text(
            "✅ Оплата прошла! Твоё стихотворение готово. ✍️",
            parse_mode="Markdown"
        )
        await check_achievements(user.id, 'poem', context)

    elif payment_type == "bundle":
        await db.add_bonus_valentines(user.id, 5)
        await update.message.reply_text(
            "✅ Отлично! Тебе добавлено **5 валентинок**.\n"
            "Теперь ты можешь отправить их своим друзьям! 💌",
            parse_mode="Markdown"
        )
        await check_achievements(user.id, 'bundle', context)

    elif payment_type == "premium":
        await update.message.reply_text(
            "✅ Премиум-оформление активировано! ✨",
            parse_mode="Markdown"
        )

    elif payment_type == "compat":
        # Start compatibility questions
        test_id = parts[1] if len(parts) > 1 else context.user_data.get('compat_test_id')
        if test_id:
            await db.mark_compat_paid(test_id)
            from handlers.compatibility import start_compat_questions
            await start_compat_questions(update, context, test_id, is_partner=False)

    elif payment_type == "voice":
        await update.message.reply_text(
            "✅ Голосовая валентинка оплачена! 🎤",
            parse_mode="Markdown"
        )

    elif payment_type == "schedule":
        schedule_time = context.user_data.get('schedule_time')
        await update.message.reply_text(
            f"✅ Отложенная доставка активирована! ⏰\n\n"
            f"Валентинка будет доставлена в указанное время.\n"
            f"Теперь отправь валентинку через меню — она будет отложена!",
            parse_mode="Markdown"
        )
        context.user_data['schedule_active'] = True

    elif payment_type == "gift":
        # Gift was attached
        gift_emoji = parts[2] if len(parts) > 2 else "🎁"
        gift_valentine_id = parts[1] if len(parts) > 1 else None

        if gift_valentine_id and gift_valentine_id.isdigit():
            # Update valentine with gift
            async with __import__('aiosqlite').connect(db.DATABASE_PATH) as conn:
                await conn.execute(
                    "UPDATE valentines SET gift_emoji = ? WHERE id = ?",
                    (gift_emoji, int(gift_valentine_id))
                )
                await conn.commit()

        await update.message.reply_text(
            f"✅ Подарок {gift_emoji} прикреплён! 🎁",
            parse_mode="Markdown"
        )
        await check_achievements(user.id, 'gift', context)

    elif payment_type == "horoscope":
        from handlers.horoscope import show_detailed_horoscope
        await show_detailed_horoscope(update, context)

    elif payment_type == "sub":
        # sub_romantic_userid or sub_lovebomb_userid or sub_lovebomb3m_userid
        # parts: ['sub', 'romantic'/'lovebomb'/'lovebomb3m', user_id]
        if len(parts) >= 2:
            plan_key = parts[1]
            days = 30
            if plan_key == "lovebomb3m":
                plan_key = "lovebomb"
                days = 90
            await db.create_subscription(user.id, plan_key, days, charge_id)
            await db.record_payment(
                user_id=user.id, amount=amount,
                payment_type=f"sub_{plan_key}", charge_id=charge_id
            )
            plan_labels = {
                "romantic": "Romantic 💕",
                "lovebomb": "Lovebomb 💣",
            }
            plan_label = plan_labels.get(plan_key, plan_key)
            months = days // 30
            await update.message.reply_text(
                f"🎉 **Подписка {plan_label} активирована!**\n\n"
                f"Действует **{months} мес.**\n"
                f"Приятного использования! ✨",
                parse_mode="Markdown"
            )
            await check_achievements(user.id, 'subscriber', context)

    elif payment_type == "weekbundle":
        await db.activate_weekly_bundle(user.id)
        await update.message.reply_text(
            "🎁 **Недельный бандл активирован!**\n\n"
            "✅ +20 валентинок добавлено\n"
            "✅ Рулетка бесплатно на 7 дней\n\n"
            "Отправляй больше, общайся! 💌",
            parse_mode="Markdown"
        )

    elif payment_type == "roulette":
        # Extra roulette match - flag in user_data so roulette handler proceeds
        context.user_data['roulette_paid'] = True
        await update.message.reply_text(
            "✅ Матч оплачен! 🎰\n\n"
            "Нажми **Рулетка** в меню — матч будет засчитан бесплатно.",
            parse_mode="Markdown"
        )


async def process_reveal_payment(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  valentine_id: int):
    """Process reveal after successful payment"""
    await db.reveal_sender(valentine_id)

    valentine = await db.get_valentine(valentine_id)
    sender = await db.get_or_create_user(valentine['sender_id'])

    await update.message.reply_text(
        SENDER_REVEALED_TEXT.format(
            name=sender['first_name'] or "Пользователь",
            username=sender['username'] or "скрыт"
        ),
        parse_mode="Markdown"
    )


async def buy_bundle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create invoice for bundle purchase"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    prices = [LabeledPrice(label="Пакет 5 валентинок", amount=BUNDLE_PRICE)]

    await context.bot.send_invoice(
        chat_id=user.id,
        title="Пакет 5 валентинок 💌",
        description="5 дополнительных валентинок для отправки друзьям!",
        payload=f"bundle_{user.id}",
        currency="XTR",
        prices=prices,
    )


async def buy_weekly_bundle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create invoice for weekly bundle"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    prices = [LabeledPrice(label="Недельный бандл", amount=WEEKLY_BUNDLE_PRICE)]

    await context.bot.send_invoice(
        chat_id=user.id,
        title="Недельный бандл 🎁",
        description="20 валентинок + рулетка бесплатно на 7 дней!",
        payload=f"weekbundle_{user.id}",
        currency="XTR",
        prices=prices,
    )


async def buy_roulette_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create invoice for extra roulette match"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    prices = [LabeledPrice(label="Доп. матч в рулетке", amount=ROULETTE_EXTRA_PRICE)]

    await context.bot.send_invoice(
        chat_id=user.id,
        title="Доп. матч в рулетке 🎰",
        description="Ещё один анонимный обмен валентинками!",
        payload=f"roulette_{user.id}",
        currency="XTR",
        prices=prices,
    )


def get_payment_handlers():
    """Return payment-related handlers"""
    return [
        PreCheckoutQueryHandler(pre_checkout_callback),
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback),
        CallbackQueryHandler(buy_bundle, pattern="^buy_bundle$"),
        CallbackQueryHandler(buy_weekly_bundle, pattern="^buy_weekbundle$"),
        CallbackQueryHandler(buy_roulette_extra, pattern="^buy_roulette_extra$"),
    ]
