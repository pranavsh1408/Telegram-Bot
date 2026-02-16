"""
Telegram Webhook Handler for Vercel Serverless.
Handles incoming updates from Telegram via webhook.
"""

import os
import json
from http.server import BaseHTTPRequestHandler
import requests
from datetime import datetime

# Get token from environment
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
KV_REST_API_URL = os.environ.get("KV_REST_API_URL", "")
KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
STANSHOP_PRODUCT_URL = "https://www.stanshop.co/in/product/phonepe-gift-voucher"


def kv_get(key):
    """Get value from Vercel KV."""
    if not KV_REST_API_URL or not KV_REST_API_TOKEN:
        return None
    try:
        resp = requests.get(
            f"{KV_REST_API_URL}/get/{key}",
            headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("result")
            if result:
                # Handle both string and dict responses
                if isinstance(result, str):
                    return json.loads(result)
                return result  # Already a dict/list
        return None
    except Exception as e:
        print(f"KV get error: {e}")
        return None


def kv_set(key, value):
    """Set value in Vercel KV."""
    if not KV_REST_API_URL or not KV_REST_API_TOKEN:
        print("KV not configured")
        return False
    try:
        # Serialize value to JSON string for storage
        json_value = json.dumps(value)
        resp = requests.post(
            f"{KV_REST_API_URL}/set/{key}",
            headers={
                "Authorization": f"Bearer {KV_REST_API_TOKEN}",
                "Content-Type": "application/json"
            },
            data=json_value,  # Send as raw JSON string, not double-encoded
            timeout=5
        )
        print(f"KV set response: {resp.status_code}")
        return resp.status_code == 200
    except Exception as e:
        print(f"KV set error: {e}")
        return False


def load_tracked_users():
    """Load tracked users from KV storage."""
    users = kv_get("tracked_users")
    
    # Handle corrupted data - if it's a string, try to parse it
    if isinstance(users, str):
        try:
            users = json.loads(users)
        except:
            print(f"Corrupted users data, resetting")
            users = {}
    
    # Validate structure - each user entry should be a dict
    if isinstance(users, dict):
        cleaned = {}
        for chat_id, data in users.items():
            if isinstance(data, dict):
                cleaned[chat_id] = data
            elif isinstance(data, str):
                try:
                    cleaned[chat_id] = json.loads(data)
                except:
                    pass  # Skip corrupted entry
        return cleaned
    
    return {} if not users else users


def save_tracked_users(users):
    """Save tracked users to KV storage."""
    kv_set("tracked_users", users)


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


def is_user_tracking(chat_id):
    """Check if a user is currently tracking."""
    users = load_tracked_users()
    return str(chat_id) in users


def get_user_status(chat_id):
    """Get tracking status for a user."""
    users = load_tracked_users()
    return users.get(str(chat_id))


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


def check_stock():
    """Check PhonePe voucher stock."""
    try:
        api_url = "https://api.getstan.app/api/v1/shop/store/inventory/slug/phonepe-gift-voucher"
        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            inventory = data.get("inventory", {})
            denominations = inventory.get("stanValueDenomination", [])
            
            if denominations:
                # Filter for active denominations
                active = [d for d in denominations if d.get("status") == "active"]
                if active:
                    msg = "🎉 *PhonePe Vouchers Available!*\n\n"
                    for d in active:
                        value = d.get("value", "Unknown")
                        price_info = d.get("price", {})
                        price = price_info.get("amount", 0) if isinstance(price_info, dict) else price_info
                        msg += f"💰 ₹{value}"
                        if price:
                            msg += f" - Price: ₹{price}"
                        msg += "\n"
                    msg += f"\n🔗 [Buy Now]({STANSHOP_PRODUCT_URL})"
                    return {"available": True, "message": msg}
            return {"available": False, "message": "📭 *No vouchers currently available*"}
        return {"available": False, "message": "⚠️ Could not check stock. Try again later."}
    except Exception as e:
        return {"available": False, "message": f"⚠️ Error checking stock: {str(e)}"}


def handle_command(chat_id, command, username=None):
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
        if not KV_REST_API_URL:
            send_message(chat_id, "⚠️ Tracking is not configured. Contact the bot admin.")
            return
            
        if is_user_tracking(chat_id):
            user_data = get_user_status(chat_id)
            if user_data and user_data.get("notified"):
                add_tracked_user(chat_id, username)
                send_message(chat_id, "🔄 *Tracking Reset!*\n\nI'll notify you when new stock arrives.")
            else:
                send_message(chat_id, "✅ You're already tracking!\n\nUse /untrack to stop.")
        else:
            add_tracked_user(chat_id, username)
            send_message(chat_id, "🔔 *Tracking Started!*\n\nI'll notify you when vouchers become available.")
    
    elif command == "/untrack":
        if remove_tracked_user(chat_id):
            send_message(chat_id, "🔕 *Tracking Stopped*\n\nUse /track to start again.")
        else:
            send_message(chat_id, "ℹ️ You weren't tracking.\nUse /track to start.")
    
    elif command == "/check":
        send_message(chat_id, "🔍 Checking stock...")
        result = check_stock()
        send_message(chat_id, result["message"])
    
    elif command == "/status":
        if is_user_tracking(chat_id):
            user_data = get_user_status(chat_id)
            if user_data and user_data.get("notified"):
                track_status = "⚠️ Notified (use /track to re-enable)"
            else:
                track_status = "✅ Active"
        else:
            track_status = "❌ Not tracking"
        
        send_message(chat_id, f"""
📊 *Your Status*

🔔 Tracking: {track_status}
🔄 Check interval: Daily at 12 PM IST
""")
    
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
                command = text.split()[0].split("@")[0]
                handle_command(chat_id, command, username)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
            
        except Exception as e:
            print(f"Webhook error: {e}")
            self.send_response(200)
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
            "token_set": bool(TELEGRAM_BOT_TOKEN),
            "kv_configured": bool(KV_REST_API_URL)
        }
        self.wfile.write(json.dumps(status).encode())
