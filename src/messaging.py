# Step 9: src/messaging.py (no explanations)
from flask import Blueprint, g, redirect, url_for, render_template, request, flash
from bson.objectid import ObjectId
from datetime import datetime
from src.utils.db import get_db

messaging_blueprint = Blueprint("messaging", __name__)
db = get_db()

def login_required(f):
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth.login_user"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@messaging_blueprint.route("/")
@login_required
def messaging_home():
    family_id = ObjectId(g.user["family_id"])
    messages = list(db.messages.find({"family_id": family_id}).sort("timestamp", -1).limit(50))
    messages.reverse()
    return render_template("messaging_home.html", messages=messages)

@messaging_blueprint.route("/send", methods=["POST"])
@login_required
def send_message():
    family_id = ObjectId(g.user["family_id"])
    sender_id = ObjectId(g.user["user_id"])
    content = request.form.get("content")
    family = db.families.find_one({"_id": family_id})
    recipient_ids = [m for m in family["members"] if m != sender_id]

    db.messages.insert_one({
        "family_id": family_id,
        "sender_id": sender_id,
        "recipient_ids": recipient_ids,
        "content": content,
        "timestamp": datetime.utcnow(),
        "read_by": [sender_id]
    })
    flash("Message sent!")
    return redirect(url_for("messaging.messaging_home"))

@messaging_blueprint.route("/read/<message_id>", methods=["POST"])
@login_required
def read_message(message_id):
    family_id = ObjectId(g.user["family_id"])
    user_id = ObjectId(g.user["user_id"])
    db.messages.update_one({"_id": ObjectId(message_id), "family_id": family_id},
                           {"$addToSet": {"read_by": user_id}})
    flash("Message marked as read")
    return redirect(url_for("messaging.messaging_home"))
