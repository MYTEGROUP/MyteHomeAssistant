# Step 6: src/calendar.py (no explanations, final integrated code)
from flask import Blueprint, render_template, request, redirect, url_for, g, flash
from bson.objectid import ObjectId
from src.utils.db import get_db

db = get_db()
calendar_blueprint = Blueprint("calendar", __name__)

def login_required(f):
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth.login_user"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@calendar_blueprint.route("/view")
@login_required
def view_calendar():
    family_id = ObjectId(g.user["family_id"])
    events = list(db.events.find({"family_id": family_id}).sort("date", 1))
    return render_template("calendar.html", events=events)

@calendar_blueprint.route("/search")
@login_required
def search_events():
    query = request.args.get("q", "")
    family_id = ObjectId(g.user["family_id"])
    events = list(db.events.find({
        "family_id": family_id,
        "$or": [
            {"title": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    }))
    return render_template("calendar.html", events=events)

@calendar_blueprint.route("/add", methods=["GET","POST"])
@login_required
def add_event():
    if request.method == "POST":
        family_id = ObjectId(g.user["family_id"])
        title = request.form.get("title")
        date = request.form.get("date")
        time = request.form.get("time")
        description = request.form.get("description")
        category = request.form.get("category", "family")
        visibility = request.form.get("visibility", "family")
        recurrence = request.form.get("recurrence", "none")

        new_event = {
            "family_id": family_id,
            "user_id": ObjectId(g.user["user_id"]),
            "title": title,
            "date": date,
            "time": time,
            "description": description,
            "category": category,
            "visibility": visibility,
            "recurrence": recurrence
        }
        db.events.insert_one(new_event)
        flash("Event added!")
        return redirect(url_for("calendar.view_calendar"))

    return render_template("add_event.html")

@calendar_blueprint.route("/edit/<event_id>", methods=["GET","POST"])
@login_required
def edit_event(event_id):
    family_id = ObjectId(g.user["family_id"])
    event = db.events.find_one({"_id": ObjectId(event_id), "family_id": family_id})
    if not event:
        return "Event not found", 404

    if request.method == "POST":
        title = request.form.get("title")
        date = request.form.get("date")
        time = request.form.get("time")
        description = request.form.get("description")
        db.events.update_one({"_id": ObjectId(event_id)}, {"$set": {
            "title": title,
            "date": date,
            "time": time,
            "description": description
        }})
        flash("Event updated!")
        return redirect(url_for("calendar.view_calendar"))

    return render_template("edit_event.html", event=event)

@calendar_blueprint.route("/delete/<event_id>", methods=["POST"])
@login_required
def delete_event(event_id):
    family_id = ObjectId(g.user["family_id"])
    result = db.events.delete_one({"_id": ObjectId(event_id), "family_id": family_id})
    if result.deleted_count:
        flash("Event deleted!")
    else:
        flash("Event not found.")
    return redirect(url_for("calendar.view_calendar"))

@calendar_blueprint.route("/events_api")
@login_required
def events_api():
    family_id = ObjectId(g.user["family_id"])
    events = list(db.events.find({"family_id": family_id}))
    fullcal_events = []
    for e in events:
        fullcal_events.append({
            "title": e["title"],
            "start": f"{e['date']}T{e['time']}",
            "description": e.get("description",""),
            "color": "#f00" if e.get("visibility","family") == "personal" else "#0f0"
        })
    return {"events": fullcal_events}
