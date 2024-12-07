# Step 5: src/family.py (no explanations, final integrated code)
from flask import Blueprint, g, redirect, url_for, render_template, request, flash
from bson.objectid import ObjectId
from src.utils.db import get_db

family_blueprint = Blueprint("family", __name__)
db = get_db()

def login_required(f):
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth.login_user"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@family_blueprint.route("/members")
@login_required
def family_members():
    family_id = ObjectId(g.user["family_id"])
    family = db.families.find_one({"_id": family_id})
    member_ids = family["members"]
    members = list(db.users.find({"_id": {"$in": member_ids}}))
    return render_template("family_members.html", members=members, family=family)

@family_blueprint.route("/invite", methods=["GET","POST"])
@login_required
def invite_member():
    family_id = ObjectId(g.user["family_id"])
    family = db.families.find_one({"_id": family_id})
    invite_code = family["invite_code"]
    return render_template("invite_code.html", invite_code=invite_code)

@family_blueprint.route("/search", methods=["GET","POST"])
@login_required
def search_family():
    if request.method == "POST":
        invite_code = request.form.get("invite_code")
        family = db.families.find_one({"invite_code": invite_code})
        if family:
            return render_template("family_search_results.html", family=family)
        else:
            flash("Family not found.")
    return render_template("family_search.html")

@family_blueprint.route("/join/<fid>", methods=["POST"])
@login_required
def join_family(fid):
    family = db.families.find_one({"_id": ObjectId(fid)})
    if not family:
        flash("Family not found.")
        return redirect(url_for("family.search_family"))
    user_id = ObjectId(g.user["user_id"])
    user = db.users.find_one({"_id": user_id})
    if "original_family_id" not in user:
        db.users.update_one({"_id": user_id}, {"$set": {"original_family_id": user["family_id"]}})
    db.users.update_one({"_id": user_id}, {"$set": {"current_family_id": family["_id"], "family_id": family["_id"]}})
    db.families.update_one({"_id": family["_id"]}, {"$addToSet": {"members": user_id}})
    flash("You have joined the family!")
    return redirect(url_for("family.family_members"))

@family_blueprint.route("/preferences", methods=["GET","POST"])
@login_required
def update_preferences():
    user_id = ObjectId(g.user["user_id"])
    user = db.users.find_one({"_id": user_id})
    if request.method == "POST":
        tasks_shared = bool(request.form.get("tasks_shared"))
        meals_shared = bool(request.form.get("meals_shared"))
        budget_shared = bool(request.form.get("budget_shared"))
        db.users.update_one({"_id": user_id}, {"$set": {
            "shared_features.tasks": tasks_shared,
            "shared_features.meals": meals_shared,
            "shared_features.budget": budget_shared,
        }})
        flash("Preferences updated!")
        return redirect(url_for("family.family_members"))
    return render_template("preferences.html", user=user)
