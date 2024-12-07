# src/family.py
from flask import Blueprint, g, redirect, url_for, render_template, request, flash
from bson.objectid import ObjectId
from src.utils.db import get_db
from src.utils.security import login_required

family_blueprint = Blueprint("family", __name__)
db = get_db()

def is_parent(user_id):
    user = db.users.find_one({"_id": ObjectId(user_id)})
    return user.get("role", "child") == "parent"

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

# New routes for managing groups
@family_blueprint.route("/groups", methods=["GET", "POST"])
@login_required
def manage_groups():
    family_id = ObjectId(g.user["family_id"])
    if request.method == "POST":
        if not is_parent(g.user["user_id"]):
            flash("Only a parent can create groups.")
            return redirect(url_for("family.manage_groups"))
        group_name = request.form.get("group_name")
        if not group_name:
            flash("Group name required.")
            return redirect(url_for("family.manage_groups"))
        db.groups.insert_one({"family_id": family_id, "name": group_name, "members": []})
        flash("Group created!")
        return redirect(url_for("family.manage_groups"))

    groups = list(db.groups.find({"family_id": family_id}))
    return render_template("groups.html", groups=groups)

@family_blueprint.route("/group/<group_id>/add_member", methods=["POST"])
@login_required
def add_group_member(group_id):
    if not is_parent(g.user["user_id"]):
        flash("Only a parent can manage groups.")
        return redirect(url_for("family.manage_groups"))

    family_id = ObjectId(g.user["family_id"])
    group = db.groups.find_one({"_id": ObjectId(group_id), "family_id": family_id})
    if not group:
        flash("Group not found.")
        return redirect(url_for("family.manage_groups"))
    member_id = request.form.get("member_id")
    if member_id:
        db.groups.update_one({"_id": group["_id"]}, {"$addToSet": {"members": ObjectId(member_id)}})
        flash("Member added to group!")
    return redirect(url_for("family.manage_groups"))

@family_blueprint.route("/group/<group_id>/remove_member/<member_id>", methods=["POST"])
@login_required
def remove_group_member(group_id, member_id):
    if not is_parent(g.user["user_id"]):
        flash("Only a parent can manage groups.")
        return redirect(url_for("family.manage_groups"))
    family_id = ObjectId(g.user["family_id"])
    group = db.groups.find_one({"_id": ObjectId(group_id), "family_id": family_id})
    if not group:
        flash("Group not found.")
        return redirect(url_for("family.manage_groups"))
    db.groups.update_one({"_id": group["_id"]}, {"$pull": {"members": ObjectId(member_id)}})
    flash("Member removed from group.")
    return redirect(url_for("family.manage_groups"))
