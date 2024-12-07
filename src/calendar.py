from flask import Blueprint, render_template, request, redirect, url_for, g, flash, send_file
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from src.utils.db import get_db
from ics import Calendar, Event as ICSEvent
import io
from src.utils.mailer import send_email

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

    # Filters from query params
    search = request.args.get("search", "")
    category = request.args.get("category", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    query = {"family_id": family_id}

    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    if category:
        query["category"] = category

    # Date filtering
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    elif start_date:
        query["date"] = {"$gte": start_date}
    elif end_date:
        query["date"] = {"$lte": end_date}

    events = list(db.events.find(query).sort("date", 1))
    # Convert ObjectIds to strings
    for ev in events:
        ev["_id"] = str(ev["_id"])

    categories = db.events.distinct("category", {"family_id": family_id})

    return render_template(
        "calendar.html",
        events=events,
        categories=categories,
        search=search,
        category=category,
        start_date=start_date,
        end_date=end_date
    )

@calendar_blueprint.route("/add", methods=["GET","POST"])
@login_required
def add_event():
    family_id = ObjectId(g.user["family_id"])
    user_id = ObjectId(g.user["user_id"])
    if request.method == "POST":
        title = request.form.get("title")
        date = request.form.get("date")
        time = request.form.get("time", "00:00")
        description = request.form.get("description", "")
        category = request.form.get("category", "general")
        visibility = request.form.get("visibility", "family")
        recurrence = request.form.get("recurrence", "none")
        color = request.form.get("color", "#378006")

        new_event = {
            "family_id": family_id,
            "user_id": user_id,
            "title": title,
            "date": date,
            "time": time,
            "description": description,
            "category": category,
            "visibility": visibility,
            "recurrence": recurrence,
            "color": color
        }

        inserted_ids = []
        if recurrence in ["daily", "weekly", "monthly"]:
            base_date = datetime.strptime(date, "%Y-%m-%d")
            increments = {
                "daily": 1,
                "weekly": 7,
                "monthly": 30
            }
            for i in range(4):
                dt = base_date + timedelta(days=increments[recurrence] * i)
                ev = new_event.copy()
                ev["date"] = dt.strftime("%Y-%m-%d")
                inserted_id = db.events.insert_one(ev).inserted_id
                inserted_ids.append(inserted_id)
        else:
            inserted_id = db.events.insert_one(new_event).inserted_id
            inserted_ids.append(inserted_id)

        # Send email notifications to family members after creating events
        family = db.families.find_one({"_id": family_id})
        members = db.users.find({"_id": {"$in": family["members"]}})
        subject = "New Event(s) Added"
        body = f"Hello,\n\nNew event(s) have been added to your family calendar:\n\nTitle: {title}\nDate: {date} {time}\nDescription: {description}\n\nLogin to view more details."
        for m in members:
            send_email(m["email"], subject, body)

        flash("Event(s) added and family notified!")
        return redirect(url_for("calendar.view_calendar"))

    return render_template("add_event.html")

@calendar_blueprint.route("/edit/<event_id>", methods=["GET","POST"])
@login_required
def edit_event(event_id):
    family_id = ObjectId(g.user["family_id"])
    obj_id = ObjectId(event_id)
    event = db.events.find_one({"_id": obj_id, "family_id": family_id})
    if not event:
        return "Event not found", 404

    if request.method == "POST":
        title = request.form.get("title")
        date = request.form.get("date")
        time = request.form.get("time")
        description = request.form.get("description", "")
        category = request.form.get("category", "general")
        color = request.form.get("color", "#378006")

        db.events.update_one({"_id": obj_id}, {"$set": {
            "title": title,
            "date": date,
            "time": time,
            "description": description,
            "category": category,
            "color": color
        }})
        flash("Event updated!")
        return redirect(url_for("calendar.view_calendar"))

    event["_id"] = str(event["_id"])
    return render_template("edit_event.html", event=event)

@calendar_blueprint.route("/delete/<event_id>", methods=["POST"])
@login_required
def delete_event(event_id):
    family_id = ObjectId(g.user["family_id"])
    obj_id = ObjectId(event_id)
    result = db.events.delete_one({"_id": obj_id, "family_id": family_id})
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
        start = f"{e['date']}T{e['time']}"
        fullcal_events.append({
            "title": e["title"],
            "start": start,
            "description": e.get("description",""),
            "color": e.get("color", "#378006")
        })
    return {"events": fullcal_events}

@calendar_blueprint.route("/import_ics", methods=["GET","POST"])
@login_required
def import_ics():
    if request.method == "POST":
        file = request.files.get("ics_file")
        if not file:
            flash("No ICS file provided.")
            return redirect(url_for("calendar.view_calendar"))

        data = file.read().decode("utf-8")
        c = Calendar(data)
        family_id = ObjectId(g.user["family_id"])
        for ev in c.events:
            event_date = ev.begin.date().strftime("%Y-%m-%d")
            event_time = ev.begin.time().strftime("%H:%M") if ev.begin.time() else "00:00"
            new_event = {
                "family_id": family_id,
                "user_id": ObjectId(g.user["user_id"]),
                "title": ev.name,
                "date": event_date,
                "time": event_time,
                "description": ev.description if ev.description else "",
                "category": "imported",
                "visibility": "family",
                "recurrence": "none",
                "color": "#0000FF"
            }
            db.events.insert_one(new_event)
        flash("ICS file imported successfully!")
        return redirect(url_for("calendar.view_calendar"))

    return render_template("import_ics.html")

@calendar_blueprint.route("/export_ics")
@login_required
def export_ics():
    family_id = ObjectId(g.user["family_id"])
    events = list(db.events.find({"family_id": family_id}))
    c = Calendar()
    for e in events:
        ev = ICSEvent()
        dt_str = f"{e['date']} {e['time']}"
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        ev.name = e["title"]
        ev.begin = dt
        ev.description = e.get("description", "")
        c.events.add(ev)
    output = io.StringIO(str(c))
    mem = io.BytesIO(output.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, download_name="family_calendar.ics", as_attachment=True, mimetype="text/calendar")
