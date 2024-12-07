# src/utils/notifications.py
from datetime import datetime
from bson.objectid import ObjectId
from src.utils.db import get_db

db = get_db()

def send_notification(user_id, message):
    """Send a notification to a specific user."""
    db.notifications.insert_one({
        "user_id": ObjectId(user_id),
        "message": message,
        "read": False,
        "timestamp": datetime.utcnow()
    })

def parse_mentions(text, family_members):
    """Parse @mentions from text. Returns a list of user_ids mentioned.
       family_members: list of user docs with 'username' and '_id'.
    """
    mentions = []
    # Extract words starting with '@'
    words = text.split()
    for w in words:
        if w.startswith("@"):
            username = w[1:]
            for m in family_members:
                if m.get("username") == username:
                    mentions.append(str(m["_id"]))
    return mentions

def notify_mentions(mentioned_user_ids, message):
    """Send notification to all mentioned users."""
    for uid in mentioned_user_ids:
        send_notification(uid, message)
