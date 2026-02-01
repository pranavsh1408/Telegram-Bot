"""
Telegram Webhook Handler for Vercel Serverless.
Handles incoming updates from Telegram via webhook.
"""

import os
import json
import asyncio
from http.server import BaseHTTPRequestHandler
import requests

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TELEGRAM_BOT_TOKEN, STANSHOP_PRODUCT_URL
from monitor import check_availability, get_last_check_time
from api.storage import (
    add_tracked_user, remove_tracked_user, is_user_tracking,
    get_user_status, load_tracked_users
)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(chat_id, text, parse_mode="Markdown"):
    """Send a message via Telegram API."""
    url = f"{TELEGRAM_API}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    requests.post(url, json=data)


async def handle_command(chat_id, command, username=None):
    """Handle bot commands."""
    
    if command == "/start" or command == "/help":
        send_message(chat_id, f"""
🎯 *PhonePe Voucher Tracker Bot*

Welcome! I'll help you track PhonePe gift voucher availability.

*Commands:*
/track - Start tracking for stock alerts
/untrack - Stop tracking
/check - Check current stock status
/status - View your tracking status
/help - Show this help message

🔗 [View on StanShop]({STANSHOP_PRODUCT_URL})
""")
    
    elif command == "/track":
        if await is_user_tracking(chat_id):
            user_data = await get_user_status(chat_id)
            if user_data and user_data.get("notified"):
                await add_tracked_user(chat_id, username)
                send_message(chat_id, "🔄 *Tracking Reset!*\n\nI'll notify you when new stock arrives.")
            else:
                send_message(chat_id, "✅ You're already tracking!\n\nUse /untrack to stop.")
        else:
            await add_tracked_user(chat_id, username)
            send_message(chat_id, "🔔 *Tracking Started!*\n\nI'll notify you when vouchers become available.")
    
    elif command == "/untrack":
        if await remove_tracked_user(chat_id):
            send_message(chat_id, "🔕 *Tracking Stopped*\n\nUse /track to start again.")
        else:
            send_message(chat_id, "ℹ️ You weren't tracking.\nUse /track to start.")
    
    elif command == "/check":
        send_message(chat_id, "🔍 Checking stock...")
        status = check_availability()
        send_message(chat_id, status["message"])
    
    elif command == "/status":
        if await is_user_tracking(chat_id):
            user_data = await get_user_status(chat_id)
            if user_data and user_data.get("notified"):
                track_status = "⚠️ Notified (use /track to re-enable)"
            else:
                track_status = "✅ Active"
        else:
            track_status = "❌ Not tracking"
        
        send_message(chat_id, f"""
📊 *Your Status*

🔔 Tracking: {track_status}
🔄 Check interval: Every 6 hours
""")


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def do_POST(self):
        """Handle incoming webhook POST from Telegram."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            update = json.loads(body.decode('utf-8'))
            
            # Extract message info
            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")
            username = message.get("from", {}).get("username")
            
            if chat_id and text.startswith("/"):
                command = text.split()[0].split("@")[0]  # Handle /command@botname
                asyncio.run(handle_command(chat_id, command, username))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "Bot webhook is active"}).encode())
