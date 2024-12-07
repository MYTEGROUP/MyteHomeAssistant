# src/tasks.py
from flask import Blueprint, request, render_template, redirect, url_for, g, flash, jsonify
from bson.objectid import ObjectId
from datetime import datetime
from src.utils.db import get_db
from src.utils.notifications import parse_mentions, notify_mentions
from src.utils.security import login_required

db = get_db()
tasks_blueprint = Blueprint("tasks", __name__)

def is_parent(user_id):
    user = db.users.find_one({"_id": ObjectId(user_id)})
    return user.get("role", "child") == "parent"

def current_user_role():
    user = db.users.find_one({"_id": ObjectId(g.user["user_id"])})
    return user.get("role", "child")

def get_family_members(family_id):
    family = db.families.find_one({"_id": family_id})
    return list(db.users.find({"_id": {"$in": family["members"]}}))

@tasks_blueprint.route("/", methods=["GET"])
@login_required
def all_tasks():
    family_id = ObjectId(g.user["family_id"])
    user_id = ObjectId(g.user["user_id"])
    role = current_user_role()

    query = {"family_id": family_id}
    if role == "child":
        query["assigned_to"] = user_id

    tasks = list(db.tasks.find(query).sort("due_date", 1))
    family = db.families.find_one({"_id": family_id})
    members = list(db.users.find({"_id": {"$in": family["members"]}}))
    categories = list(db.task_categories.find({"family_id": family_id}))

    # Check overdue
    for t in tasks:
        if t.get("due_date"):
            due = datetime.strptime(t["due_date"], "%Y-%m-%d")
            if due < datetime.utcnow() and t["status"] != "complete":
                t["overdue"] = True
            else:
                t["overdue"] = False
        t["_id"] = str(t["_id"])
        t["assigned_to"] = str(t["assigned_to"])
        # Convert comments user_ids to str
        if "comments" in t:
            for c in t["comments"]:
                c["user_id"] = str(c["user_id"])

    for m in members:
        m["_id"] = str(m["_id"])

    return render_template("tasks.html", tasks=tasks, role=role, members=members, categories=categories)

@tasks_blueprint.route("/ajax_create", methods=["POST"])
@login_required
def ajax_create_task():
    if not is_parent(g.user["user_id"]):
        return jsonify({"error": "Only a parent can create tasks."}), 403

    family_id = ObjectId(g.user["family_id"])
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date = request.form.get("due_date", "")
    priority = request.form.get("priority", "medium")
    assigned_to = request.form.get("assigned_to")
    category = request.form.get("category", "")
    recurring = request.form.get("recurring", "none")
    reminder_date = request.form.get("reminder_date", "")

    if not title or not assigned_to:
        return jsonify({"error": "Title and assigned_to are required"}), 400

    family_members = get_family_members(family_id)
    mentioned_user_ids = parse_mentions(description, family_members)

    new_task = {
        "family_id": family_id,
        "title": title,
        "description": description,
        "due_date": due_date,
        "status": "incomplete",
        "assigned_to": ObjectId(assigned_to),
        "priority": priority,
        "comments": [],
        "category": category,
        "recurring": recurring,
        "reminder_date": reminder_date
    }

    result = db.tasks.insert_one(new_task)
    new_task["_id"] = str(result.inserted_id)
    new_task["assigned_to"] = assigned_to

    # Notify mentioned users
    if mentioned_user_ids:
        msg = f"You were mentioned in a new task: {title}"
        notify_mentions(mentioned_user_ids, msg)

    return jsonify(new_task), 200

@tasks_blueprint.route("/inline_update/<task_id>", methods=["POST"])
@login_required
def inline_update(task_id):
    family_id = ObjectId(g.user["family_id"])
    user_id = g.user["user_id"]
    task = db.tasks.find_one({"_id": ObjectId(task_id), "family_id": family_id})
    if not task:
        return jsonify({"error": "Task not found"}), 404

    if not is_parent(user_id):
        return jsonify({"error": "Only a parent can inline update tasks."}), 403

    field = request.form.get("field")
    value = request.form.get("value")

    allowed_fields = ["title", "description", "due_date", "priority", "assigned_to", "category", "recurring", "reminder_date"]
    if field not in allowed_fields:
        return jsonify({"error": "Invalid field"}), 400

    update_value = value
    if field == "assigned_to":
        update_value = ObjectId(value)

    # If description updated, parse mentions again
    mentioned_user_ids = []
    if field == "description":
        family_members = get_family_members(family_id)
        mentioned_user_ids = parse_mentions(value, family_members)

    db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": {field: update_value}})
    updated_task = db.tasks.find_one({"_id": ObjectId(task_id)})

    # Notify mentions if description changed
    if mentioned_user_ids:
        msg = f"You were mentioned in task: {updated_task['title']}"
        notify_mentions(mentioned_user_ids, msg)

    updated_task["_id"] = str(updated_task["_id"])
    updated_task["assigned_to"] = str(updated_task["assigned_to"])
    return jsonify(updated_task), 200

@tasks_blueprint.route("/edit/<task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    family_id = ObjectId(g.user["family_id"])
    obj_id = ObjectId(task_id)
    task = db.tasks.find_one({"_id": obj_id, "family_id": family_id})
    if not task:
        return "Task not found", 404

    if not is_parent(g.user["user_id"]):
        flash("Only a parent can edit tasks.")
        return redirect(url_for("tasks.all_tasks"))

    family_members = get_family_members(family_id)

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description", "")
        due_date = request.form.get("due_date", "")
        priority = request.form.get("priority", "medium")
        assigned_to = request.form.get("assigned_to")
        category = request.form.get("category", task.get("category",""))
        recurring = request.form.get("recurring", task.get("recurring","none"))
        reminder_date = request.form.get("reminder_date", task.get("reminder_date",""))

        mentioned_user_ids = parse_mentions(description, family_members)

        update_fields = {
            "title": title,
            "description": description,
            "due_date": due_date,
            "priority": priority,
            "assigned_to": ObjectId(assigned_to),
            "category": category,
            "recurring": recurring,
            "reminder_date": reminder_date
        }
        db.tasks.update_one({"_id": obj_id}, {"$set": update_fields})
        flash("Task updated successfully!")

        if mentioned_user_ids:
            msg = f"You were mentioned in the updated task: {title}"
            notify_mentions(mentioned_user_ids, msg)

        return redirect(url_for("tasks.all_tasks"))

    task["_id"] = str(task["_id"])
    task["assigned_to"] = str(task["assigned_to"])
    children = family_members
    return render_template("edit_task.html", task=task, children=children)

@tasks_blueprint.route("/delete/<task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    family_id = ObjectId(g.user["family_id"])
    if not is_parent(g.user["user_id"]):
        flash("Only a parent can delete tasks.")
        return redirect(url_for("tasks.all_tasks"))

    obj_id = ObjectId(task_id)
    result = db.tasks.delete_one({"_id": obj_id, "family_id": family_id})
    if result.deleted_count == 1:
        flash("Task deleted successfully!")
    else:
        flash("Task not found or could not be deleted.")
    return redirect(url_for("tasks.all_tasks"))

@tasks_blueprint.route("/complete/<task_id>", methods=["POST"])
@login_required
def complete_task(task_id):
    user_id = ObjectId(g.user["user_id"])
    family_id = ObjectId(g.user["family_id"])
    obj_id = ObjectId(task_id)
    task = db.tasks.find_one({"_id": obj_id, "family_id": family_id})
    if not task:
        return "Task not found", 404
    if task["assigned_to"] != user_id:
        return "You are not assigned to this task", 403

    db.tasks.update_one({"_id": obj_id}, {"$set": {"status": "complete"}})
    flash("Task marked as complete!")
    return redirect(url_for("tasks.all_tasks"))

@tasks_blueprint.route("/in_progress/<task_id>", methods=["POST"])
@login_required
def in_progress_task(task_id):
    user_id = ObjectId(g.user["user_id"])
    family_id = ObjectId(g.user["family_id"])
    obj_id = ObjectId(task_id)
    task = db.tasks.find_one({"_id": obj_id, "family_id": family_id})
    if not task:
        return "Task not found", 404
    if task["assigned_to"] != user_id:
        return "You are not assigned to this task", 403

    db.tasks.update_one({"_id": obj_id}, {"$set": {"status": "in_progress"}})
    flash("Task marked as in progress!")
    return redirect(url_for("tasks.all_tasks"))

@tasks_blueprint.route("/comment/<task_id>", methods=["POST"])
@login_required
def add_comment(task_id):
    user_id = ObjectId(g.user["user_id"])
    family_id = ObjectId(g.user["family_id"])
    obj_id = ObjectId(task_id)
    task = db.tasks.find_one({"_id": obj_id, "family_id": family_id})
    if not task:
        return "Task not found", 404

    comment_text = request.form.get("comment")
    if not comment_text:
        flash("Comment cannot be empty.")
        return redirect(url_for("tasks.all_tasks"))

    family_members = get_family_members(family_id)
    mentioned_user_ids = parse_mentions(comment_text, family_members)

    comment = {
        "user_id": user_id,
        "comment": comment_text,
        "timestamp": datetime.utcnow()
    }
    db.tasks.update_one({"_id": obj_id}, {"$push": {"comments": comment}})

    if mentioned_user_ids:
        msg = f"You were mentioned in a comment on task: {task['title']}"
        notify_mentions(mentioned_user_ids, msg)

    flash("Comment added!")
    return redirect(url_for("tasks.all_tasks"))
