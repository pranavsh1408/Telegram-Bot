"""
Telegram Webhook Handler for Vercel Serverless.
Handles incoming updates from Telegram via webhook.
"""

import os
import json
from http.server import BaseHTTPRequestHandler
import requests

# Get token from environment
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
STANSHOP_PRODUCT_URL = "https://www.stanshop.co/in/product/phonepe-gift-voucher"


def send_message(chat_id, text, parse_mode="Markdown"):
    """Send a message via Telegram API."""
    url = f"{TELEGRAM_API}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    try:
        resp = requests.post(url, json=data, timeout=10)
        return resp.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None


def handle_command(chat_id, command, username=None):
    """Handle bot commands."""
    
    if command == "/start" or command == "/help":
        send_message(chat_id, f"""
🎯 *PhonePe Voucher Tracker Bot*

Welcome! I'll help you track PhonePe gift voucher availability.

*Commands:*
/start - Show this welcome message
/check - Check current stock status
/help - Show this help message

🔗 [View on StanShop]({STANSHOP_PRODUCT_URL})
""")
    
    elif command == "/check":
        send_message(chat_id, "🔍 Checking stock...")
        # Simple stock check
        try:
            api_url = "https://api.getstan.app/api/v1/shop/store/inventory/slug/phonepe-gift-voucher"
            resp = requests.get(api_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                variants = data.get("data", {}).get("variants", [])
                
                if variants:
                    available = [v for v in variants if v.get("available", False)]
                    if available:
                        msg = "✅ *Stock Available!*\n\n"
                        for v in available:
                            name = v.get("title", "Unknown")
                            price = v.get("price", 0) / 100
                            msg += f"• {name}: ₹{price:.0f}\n"
                        msg += f"\n🔗 [Buy Now]({STANSHOP_PRODUCT_URL})"
                        send_message(chat_id, msg)
                    else:
                        send_message(chat_id, "❌ *Out of Stock*\n\nNo vouchers currently available.")
                else:
                    send_message(chat_id, "❌ *Out of Stock*\n\nNo vouchers currently available.")
            else:
                send_message(chat_id, "⚠️ Could not check stock. Try again later.")
        except Exception as e:
            send_message(chat_id, f"⚠️ Error checking stock: {str(e)}")
    
    else:
        send_message(chat_id, "Unknown command. Use /help to see available commands.")


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def do_POST(self):
        """Handle incoming webhook POST from Telegram."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            update = json.loads(body.decode('utf-8'))
            
            # Extract message info
            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")
            username = message.get("from", {}).get("username")
            
            if chat_id and text.startswith("/"):
                command = text.split()[0].split("@")[0]  # Handle /command@botname
                handle_command(chat_id, command, username)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
            
        except Exception as e:
            print(f"Webhook error: {e}")
            self.send_response(200)  # Always return 200 to Telegram
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "error": str(e)}).encode())
    
    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        status = {
            "status": "Bot webhook is active",
            "token_set": bool(TELEGRAM_BOT_TOKEN)
        }
        self.wfile.write(json.dumps(status).encode())
