"""
Cron Job Handler for scheduled stock checks.
Called by Vercel Cron daily at 12 PM IST.
"""

import os
import re
import json
from http.server import BaseHTTPRequestHandler
import requests

# Telegram & KV config from environment
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
KV_REST_API_URL = os.environ.get("KV_REST_API_URL", "")
KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
STANSHOP_PAGE_URL = "https://www.stanshop.co/in/product/phonepe-gift-card"
STANSHOP_PRODUCT_URL = "https://www.stanshop.co/in/product/phonepe-gift-card"


# ── KV helpers (same pattern as webhook.py) ──────────────────────────

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
                if isinstance(result, str):
                    return json.loads(result)
                return result
        return None
    except Exception as e:
        print(f"KV get error: {e}")
        return None


def kv_set(key, value):
    """Set value in Vercel KV."""
    if not KV_REST_API_URL or not KV_REST_API_TOKEN:
        return False
    try:
        json_value = json.dumps(value)
        resp = requests.post(
            f"{KV_REST_API_URL}/set/{key}",
            headers={
                "Authorization": f"Bearer {KV_REST_API_TOKEN}",
                "Content-Type": "application/json"
            },
            data=json_value,
            timeout=5
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"KV set error: {e}")
        return False


def load_tracked_users():
    """Load tracked users from KV (same logic as webhook.py)."""
    users = kv_get("tracked_users")
    if isinstance(users, str):
        try:
            users = json.loads(users)
        except Exception:
            users = {}
    if isinstance(users, dict):
        cleaned = {}
        for chat_id, data in users.items():
            if isinstance(data, dict):
                cleaned[chat_id] = data
            elif isinstance(data, str):
                try:
                    cleaned[chat_id] = json.loads(data)
                except Exception:
                    pass
        return cleaned
    return {} if not users else users


def get_users_to_notify():
    """Get list of chat_ids who should receive notifications."""
    users = load_tracked_users()
    return [
        chat_id for chat_id, data in users.items()
        if not data.get("notified", False)
    ]


def mark_user_notified(chat_id):
    """Mark a user as notified in KV."""
    users = load_tracked_users()
    if str(chat_id) in users:
        users[str(chat_id)]["notified"] = True
        kv_set("tracked_users", users)


# ── Telegram helper ──────────────────────────────────────────────────

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
        print(f"Telegram send to {chat_id}: {resp.status_code}")
        return resp
    except Exception as e:
        print(f"Telegram send error: {e}")
        return None


# ── Stock check (self-contained, same as webhook.py) ─────────────────

def check_stock():
    """Check PhonePe voucher stock by scraping the product page."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
        }
        resp = requests.get(STANSHOP_PAGE_URL, headers=headers, timeout=30)
        resp.raise_for_status()
        html = resp.text

        match = re.search(r'"stanValueDenomination\\":\s*(\[.*?\])\s*,\s*\\"brandColor', html)
        if not match:
            return {"available": False, "message": "⚠️ Could not find denomination data on page."}

        raw = match.group(1).replace('\\"', '"')
        denominations = json.loads(raw)

        if denominations:
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
    except Exception as e:
        return {"available": False, "message": f"⚠️ Error checking stock: {str(e)}"}


# ── Cron handler ─────────────────────────────────────────────────────

def run_stock_check():
    """Check stock and notify all tracked (un-notified) users."""
    stock = check_stock()
    notified_count = 0
    errors = []

    users_to_notify = get_users_to_notify()
    print(f"Users to notify: {users_to_notify}")

    if not users_to_notify:
        return {
            "checked": True,
            "stock_available": stock["available"],
            "users_found": 0,
            "users_notified": 0,
            "kv_configured": bool(KV_REST_API_URL),
            "message": "No users to notify"
        }

    if stock["available"]:
        # Stock available → send alert and mark notified
        for chat_id in users_to_notify:
            try:
                message = stock["message"] + "\n\n_Tracking paused. Use /track to re-enable._"
                send_message(int(chat_id), message)
                mark_user_notified(chat_id)
                notified_count += 1
            except Exception as e:
                errors.append(f"{chat_id}: {e}")
    else:
        # Stock not available → send daily status update
        for chat_id in users_to_notify:
            try:
                send_message(
                    int(chat_id),
                    "📭 *Daily Update:* No PhonePe vouchers available right now.\n\n"
                    "I'll keep checking and notify you when stock appears! 🔔"
                )
                notified_count += 1
            except Exception as e:
                errors.append(f"{chat_id}: {e}")

    return {
        "checked": True,
        "stock_available": stock["available"],
        "users_found": len(users_to_notify),
        "users_notified": notified_count,
        "errors": errors if errors else None
    }


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler for cron."""

    def do_GET(self):
        """Handle cron trigger."""
        try:
            result = run_stock_check()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            print(f"Cron error: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_POST(self):
        """Also allow POST for manual triggers."""
        self.do_GET()
