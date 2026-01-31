"""
Telegram Bot for PhonePe Voucher Tracking.
Provides commands to check stock and receives automatic notifications.
Users must use /track to register for notifications.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN, STANSHOP_PRODUCT_URL, validate_config
from monitor import check_availability, get_last_check_time, check_for_stock_change

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot instance (set during initialization)
_application = None

# File to store tracked users
TRACKED_USERS_FILE = "tracked_users.json"


def load_tracked_users():
    """Load tracked users from file."""
    if os.path.exists(TRACKED_USERS_FILE):
        try:
            with open(TRACKED_USERS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_tracked_users(users):
    """Save tracked users to file."""
    with open(TRACKED_USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def add_tracked_user(chat_id, username=None):
    """Add a user to tracking list."""
    users = load_tracked_users()
    users[str(chat_id)] = {
        "username": username,
        "tracked_at": datetime.now().isoformat(),
        "notified": False
    }
    save_tracked_users(users)


def remove_tracked_user(chat_id):
    """Remove a user from tracking list."""
    users = load_tracked_users()
    if str(chat_id) in users:
        del users[str(chat_id)]
        save_tracked_users(users)
        return True
    return False


def mark_user_notified(chat_id):
    """Mark a user as notified (stops further notifications)."""
    users = load_tracked_users()
    if str(chat_id) in users:
        users[str(chat_id)]["notified"] = True
        save_tracked_users(users)


def get_users_to_notify():
    """Get list of users who should receive notifications (tracked but not yet notified)."""
    users = load_tracked_users()
    return [
        chat_id for chat_id, data in users.items()
        if not data.get("notified", False)
    ]


def is_user_tracking(chat_id):
    """Check if a user is currently tracking."""
    users = load_tracked_users()
    return str(chat_id) in users


def get_user_status(chat_id):
    """Get tracking status for a user."""
    users = load_tracked_users()
    return users.get(str(chat_id))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - Welcome message."""
    welcome_message = """
🎯 *PhonePe Voucher Tracker Bot*

Welcome! I'll help you track PhonePe gift voucher availability on StanShop.

*Available Commands:*
/track - Start tracking for stock alerts
/untrack - Stop tracking
/check - Check current stock status
/status - View your tracking status
/help - Show this help message

📡 Use /track to get notified when vouchers become available!

🔗 [View on StanShop]({})
""".format(STANSHOP_PRODUCT_URL)
    
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /track command - Register for notifications."""
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    
    if is_user_tracking(chat_id):
        user_data = get_user_status(chat_id)
        if user_data and user_data.get("notified"):
            # User was notified before, reset tracking
            add_tracked_user(chat_id, username)
            await update.message.reply_text(
                "🔄 *Tracking Reset!*\n\n"
                "You were previously notified about stock availability.\n"
                "I'll notify you again when new stock arrives.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "✅ You're already tracking!\n\n"
                "I'll notify you as soon as PhonePe vouchers become available.\n"
                "Use /untrack to stop tracking.",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        add_tracked_user(chat_id, username)
        await update.message.reply_text(
            "🔔 *Tracking Started!*\n\n"
            "I'll notify you as soon as PhonePe vouchers become available.\n"
            "You'll receive one notification, then tracking will stop automatically.\n\n"
            "Use /track again after being notified to re-enable tracking.\n"
            "Use /untrack to stop tracking.",
            parse_mode=ParseMode.MARKDOWN
        )


async def untrack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /untrack command - Stop tracking."""
    chat_id = update.effective_chat.id
    
    if remove_tracked_user(chat_id):
        await update.message.reply_text(
            "🔕 *Tracking Stopped*\n\n"
            "You won't receive stock notifications anymore.\n"
            "Use /track to start tracking again.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "ℹ️ You weren't tracking.\n"
            "Use /track to start tracking.",
            parse_mode=ParseMode.MARKDOWN
        )


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command - Manual stock check."""
    await update.message.reply_text("🔍 Checking stock...")
    
    status = check_availability()
    
    await update.message.reply_text(
        status["message"],
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - Show tracking status."""
    chat_id = update.effective_chat.id
    last_check = get_last_check_time()
    
    # User tracking status
    if is_user_tracking(chat_id):
        user_data = get_user_status(chat_id)
        if user_data and user_data.get("notified"):
            track_status = "⚠️ Notified (use /track to re-enable)"
        else:
            track_status = "✅ Active"
    else:
        track_status = "❌ Not tracking (use /track to start)"
    
    # Last check time
    if last_check:
        time_str = last_check.strftime("%Y-%m-%d %H:%M:%S")
        time_ago = datetime.now() - last_check
        minutes_ago = int(time_ago.total_seconds() / 60)
        
        if minutes_ago < 1:
            ago_text = "just now"
        elif minutes_ago < 60:
            ago_text = f"{minutes_ago} minutes ago"
        else:
            hours_ago = minutes_ago // 60
            ago_text = f"{hours_ago} hour(s) ago"
        
        check_info = f"⏰ Last check: {time_str}\n   ({ago_text})"
    else:
        check_info = "⏰ No checks performed yet"
    
    status_text = f"""
📊 *Your Status*

🔔 Tracking: {track_status}
{check_info}
🔄 Check interval: Every hour

Use /check to manually check now.
"""
    
    await update.message.reply_text(
        status_text,
        parse_mode=ParseMode.MARKDOWN
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command - Show help message."""
    help_text = """
📖 *Available Commands*

/track - Start tracking for stock notifications
/untrack - Stop tracking
/check - Check current PhonePe voucher stock
/status - View your tracking status
/help - Show this help message

*How it works:*
• Use /track to register for notifications
• I check StanShop every hour automatically
• When vouchers become available, you'll get ONE notification
• Tracking stops after notification (no spam!)
• Use /track again to re-enable after being notified

🔗 [StanShop PhonePe Page]({})
""".format(STANSHOP_PRODUCT_URL)
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


async def send_notification_to_users(message: str):
    """
    Send notification to all tracked users who haven't been notified yet.
    
    Args:
        message: The message to send (supports Markdown)
    
    Returns:
        int: Number of users notified
    """
    global _application
    
    if _application is None:
        logger.error("Bot application not initialized")
        return 0
    
    users_to_notify = get_users_to_notify()
    notified_count = 0
    
    for chat_id in users_to_notify:
        try:
            await _application.bot.send_message(
                chat_id=int(chat_id),
                text=message + "\n\n_Tracking paused. Use /track to re-enable._",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            mark_user_notified(chat_id)
            notified_count += 1
            logger.info(f"Notified user {chat_id}")
        except Exception as e:
            logger.error(f"Failed to notify user {chat_id}: {e}")
    
    return notified_count


async def scheduled_check():
    """
    Perform a scheduled check and send notification if stock appeared.
    Called by the scheduler.
    """
    logger.info("Running scheduled stock check...")
    
    result = check_for_stock_change()
    
    if result["changed"]:
        logger.info("Stock change detected! Sending notifications to tracked users...")
        count = await send_notification_to_users(result["status"]["message"])
        logger.info(f"Notified {count} user(s)")
    else:
        logger.info(f"No stock change. Reason: {result['reason']}")


def get_application():
    """Get the bot application instance."""
    return _application


def create_bot():
    """
    Create and configure the Telegram bot application.
    
    Returns:
        Application: Configured bot application
    """
    global _application
    
    if not validate_config():
        raise ValueError("Invalid configuration. Please check your .env file.")
    
    # Create application
    _application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    _application.add_handler(CommandHandler("start", start_command))
    _application.add_handler(CommandHandler("track", track_command))
    _application.add_handler(CommandHandler("untrack", untrack_command))
    _application.add_handler(CommandHandler("check", check_command))
    _application.add_handler(CommandHandler("status", status_command))
    _application.add_handler(CommandHandler("help", help_command))
    
    logger.info("Bot created successfully")
    return _application


async def run_bot():
    """Run the bot (for use with scheduler)."""
    app = create_bot()
    
    # Initialize and start
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("Bot is running...")
    
    return app


if __name__ == "__main__":
    # Run bot standalone (without scheduler)
    print("Starting PhonePe Voucher Tracker Bot...")
    print("Press Ctrl+C to stop")
    
    app = create_bot()
    app.run_polling()
