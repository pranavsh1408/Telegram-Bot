"""
Vercel KV Storage for tracked users.
Replaces file-based tracked_users.json for serverless environment.
"""

import os
import json
from datetime import datetime

# Try to import Vercel KV, fall back to local file for development
try:
    from vercel_kv import KV
    kv = KV()
    USE_VERCEL_KV = True
except ImportError:
    USE_VERCEL_KV = False
    kv = None

TRACKED_USERS_KEY = "tracked_users"
LOCAL_FILE = "tracked_users.json"


def _load_local():
    """Load from local file (for development)."""
    if os.path.exists(LOCAL_FILE):
        try:
            with open(LOCAL_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_local(users):
    """Save to local file (for development)."""
    with open(LOCAL_FILE, "w") as f:
        json.dump(users, f, indent=2)


async def load_tracked_users():
    """Load tracked users from storage."""
    if USE_VERCEL_KV:
        data = await kv.get(TRACKED_USERS_KEY)
        return data if data else {}
    return _load_local()


async def save_tracked_users(users):
    """Save tracked users to storage."""
    if USE_VERCEL_KV:
        await kv.set(TRACKED_USERS_KEY, users)
    else:
        _save_local(users)


async def add_tracked_user(chat_id, username=None):
    """Add a user to tracking list."""
    users = await load_tracked_users()
    users[str(chat_id)] = {
        "username": username,
        "tracked_at": datetime.now().isoformat(),
        "notified": False
    }
    await save_tracked_users(users)


async def remove_tracked_user(chat_id):
    """Remove a user from tracking list."""
    users = await load_tracked_users()
    if str(chat_id) in users:
        del users[str(chat_id)]
        await save_tracked_users(users)
        return True
    return False


async def mark_user_notified(chat_id):
    """Mark a user as notified."""
    users = await load_tracked_users()
    if str(chat_id) in users:
        users[str(chat_id)]["notified"] = True
        await save_tracked_users(users)


async def get_users_to_notify():
    """Get list of users who should receive notifications."""
    users = await load_tracked_users()
    return [
        chat_id for chat_id, data in users.items()
        if not data.get("notified", False)
    ]


async def is_user_tracking(chat_id):
    """Check if a user is currently tracking."""
    users = await load_tracked_users()
    return str(chat_id) in users


async def get_user_status(chat_id):
    """Get tracking status for a user."""
    users = await load_tracked_users()
    return users.get(str(chat_id))
