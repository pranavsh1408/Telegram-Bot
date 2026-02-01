"""
Cron Job Handler for scheduled stock checks.
Called by Vercel Cron every 6 hours.
"""

import os
import json
import asyncio
from http.server import BaseHTTPRequestHandler
import requests

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TELEGRAM_BOT_TOKEN
from monitor import check_for_stock_change
from api.storage import get_users_to_notify, mark_user_notified

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
    return requests.post(url, json=data)


async def run_stock_check():
    """
    Check for stock changes and notify users.
    Returns dict with check results.
    """
    result = check_for_stock_change()
    notified_count = 0
    
    if result["changed"]:
        # Stock became available - notify all tracked users
        users_to_notify = await get_users_to_notify()
        
        for chat_id in users_to_notify:
            try:
                message = result["status"]["message"]
                message += "\n\n_Tracking paused. Use /track to re-enable._"
                send_message(int(chat_id), message)
                await mark_user_notified(chat_id)
                notified_count += 1
            except Exception as e:
                print(f"Failed to notify {chat_id}: {e}")
    
    return {
        "checked": True,
        "stock_available": result["status"]["available"],
        "stock_changed": result["changed"],
        "users_notified": notified_count,
        "reason": result["reason"]
    }


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler for cron."""
    
    def do_GET(self):
        """Handle cron trigger."""
        # Verify cron secret (optional but recommended)
        auth_header = self.headers.get("Authorization", "")
        cron_secret = os.environ.get("CRON_SECRET", "")
        
        # If CRON_SECRET is set, verify it (Vercel sends it in Authorization header)
        if cron_secret and auth_header != f"Bearer {cron_secret}":
            # Still allow for manual testing, but log warning
            print("Warning: CRON_SECRET mismatch or missing")
        
        try:
            result = asyncio.run(run_stock_check())
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_POST(self):
        """Also allow POST for manual triggers."""
        self.do_GET()
