"""
Configuration loader for the PhonePe Voucher Tracker Bot.
Loads settings from .env file.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Monitoring Configuration
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "86400"))  # Default: 24 hours (1 day)

# StanShop API Configuration
STANSHOP_API_URL = "https://api.getstan.app/api/v1/shop/store/inventory/slug/phonepe-gift-voucher"
STANSHOP_PRODUCT_URL = "https://www.stanshop.co/in/product/phonepe-gift-voucher"


def validate_config():
    """Validate that required configuration is present."""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_bot_token_here":
        errors.append("TELEGRAM_BOT_TOKEN is not set. Please update your .env file.")
    
    # Note: TELEGRAM_CHAT_ID is optional - users register via /track command
    
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


if __name__ == "__main__":
    # Test configuration loading
    print("Configuration Test:")
    print(f"  TELEGRAM_BOT_TOKEN: {'*' * 10 if TELEGRAM_BOT_TOKEN else 'NOT SET'}")
    print(f"  TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID else 'NOT SET'}")
    print(f"  CHECK_INTERVAL: {CHECK_INTERVAL} seconds")
    print(f"  STANSHOP_API_URL: {STANSHOP_API_URL}")
    print()
    
    if validate_config():
        print("✅ Configuration is valid!")
    else:
        print("❌ Configuration has errors. Please fix them before running the bot.")
