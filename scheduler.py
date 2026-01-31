"""
Scheduler for periodic stock checks.
Runs the bot with hourly automated checks.
"""

import asyncio
import logging
import signal
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import CHECK_INTERVAL, validate_config
from bot import create_bot, scheduled_check

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def run_scheduled_check():
    """Wrapper for scheduled check to handle exceptions."""
    try:
        await scheduled_check()
    except Exception as e:
        logger.error(f"Error during scheduled check: {e}")


async def main():
    """Main entry point - runs bot with scheduler."""
    
    # Validate configuration
    if not validate_config():
        print("\n❌ Configuration error! Please set up your .env file:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your TELEGRAM_BOT_TOKEN from @BotFather")
        print("   3. Add your TELEGRAM_CHAT_ID from @userinfobot")
        return
    
    # Create bot
    app = create_bot()
    
    # Create scheduler
    scheduler = AsyncIOScheduler()
    
    # Add hourly check job
    scheduler.add_job(
        run_scheduled_check,
        trigger=IntervalTrigger(seconds=CHECK_INTERVAL),
        id="stock_check",
        name="PhonePe Voucher Stock Check",
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    logger.info(f"Scheduler started. Checking every {CHECK_INTERVAL} seconds ({CHECK_INTERVAL // 3600} hour(s))")
    
    # Initialize bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("Bot is running! Press Ctrl+C to stop.")
    
    # Run initial check (just to log current state)
    logger.info("Running initial stock check...")
    await run_scheduled_check()
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        # Cleanup
        logger.info("Shutting down...")
        scheduler.shutdown()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
