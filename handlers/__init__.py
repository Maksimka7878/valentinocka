"""
Handlers package for Valentine Bot v3.0
"""
from handlers.start import get_start_handlers
from handlers.send import get_send_handlers
from handlers.inbox import get_inbox_handlers
from handlers.reveal import get_reveal_handlers
from handlers.payment import get_payment_handlers
from handlers.poems import get_poem_handlers
from handlers.extras import get_extra_handlers
from handlers.roulette import get_roulette_handlers
from handlers.compatibility import get_compat_handlers
from handlers.horoscope import get_horoscope_handlers
from handlers.achievements import get_achievement_handlers
from handlers.subscription import get_subscription_handlers
from handlers.occasions import get_occasion_handlers


def register_all_handlers(application):
    """Register all handlers to the application"""
    # Payment handlers first (highest priority)
    for handler in get_payment_handlers():
        application.add_handler(handler)

    # ConversationHandlers MUST be registered before plain text handlers
    # so they can intercept user input during conversations
    for handler in get_send_handlers():
        application.add_handler(handler)
    for handler in get_roulette_handlers():
        application.add_handler(handler)
    for handler in get_poem_handlers():
        application.add_handler(handler)
    for handler in get_extra_handlers():
        application.add_handler(handler)

    # Feature handlers (callback-based, safe to register before text router)
    for handler in get_inbox_handlers():
        application.add_handler(handler)
    for handler in get_reveal_handlers():
        application.add_handler(handler)
    for handler in get_compat_handlers():
        application.add_handler(handler)
    for handler in get_horoscope_handlers():
        application.add_handler(handler)
    for handler in get_achievement_handlers():
        application.add_handler(handler)
    for handler in get_subscription_handlers():
        application.add_handler(handler)
    for handler in get_occasion_handlers():
        application.add_handler(handler)

    # Start, menu commands and reply-keyboard text router (lowest priority - registered last)
    for handler in get_start_handlers():
        application.add_handler(handler)
