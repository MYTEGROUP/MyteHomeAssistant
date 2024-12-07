# src/messaging.py
from flask import Blueprint, g, render_template, request, flash, redirect, url_for
from bson.objectid import ObjectId
from datetime import datetime
from src.utils.db import get_db
from src.utils.security import login_required
from src.utils.notifications import parse_mentions, notify_mentions

db = get_db()
messaging_blueprint = Blueprint("messaging", __name__)

def get_family_members(family_id):
    family = db.families.find_one({"_id": family_id})
    return list(db.users.find({"_id": {"$in": family["members"]}}))

@messaging_blueprint.route("/", methods=["GET"])
@login_required
def messaging_home():
    family_id = ObjectId(g.user["family_id"])
    messages = list(db.messages.find({"family_id": family_id}).sort("timestamp", -1).limit(50))
    for m in messages:
        m["_id"] = str(m["_id"])
        m["sender_id"] = str(m["sender_id"])
        m["recipient_ids"] = [str(r) for r in m.get("recipient_ids", [])]
    messages.reverse()
    return render_template("messaging_home.html", messages=messages)

@messaging_blueprint.route("/send", methods=["POST"])
@login_required
def send_message():
    family_id = ObjectId(g.user["family_id"])
    sender_id = ObjectId(g.user["user_id"])
    content = request.form.get("content")
    recipient_type = request.form.get("recipient_type") # family, user, group
    recipient_id = request.form.get("recipient_id") # user_id or group_id if not family

    if not content:
        flash("Message cannot be empty.")
        return redirect(url_for("messaging.messaging_home"))

    family_members = get_family_members(family_id)

    if recipient_type == "family":
        # send to entire family except sender
        family = db.families.find_one({"_id": family_id})
        recipient_ids = [m for m in family["members"] if m != sender_id]
    elif recipient_type == "user":
        recipient_ids = [ObjectId(recipient_id)]
    elif recipient_type == "group":
        grp = db.groups.find_one({"_id": ObjectId(recipient_id), "family_id": family_id})
        recipient_ids = [u for u in grp["members"] if u != sender_id]
    else:
        flash("Invalid recipient type.")
        return redirect(url_for("messaging.messaging_home"))

    mentioned_user_ids = parse_mentions(content, family_members)

    db.messages.insert_one({
        "family_id": family_id,
        "sender_id": sender_id,
        "recipient_ids": recipient_ids,
        "content": content,
        "timestamp": datetime.utcnow(),
        "read_by": [sender_id]
    })

    if mentioned_user_ids:
        msg = "You were mentioned in a new message."
        notify_mentions(mentioned_user_ids, msg)

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
