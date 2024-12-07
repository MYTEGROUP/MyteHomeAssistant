# Step 10: src/tasks.py (no explanations)
from flask import Blueprint, request, render_template, redirect, url_for, g, flash
from bson.objectid import ObjectId
from src.utils.db import get_db

db = get_db()
tasks_blueprint = Blueprint("tasks", __name__)

def login_required(f):
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth.login_user"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@tasks_blueprint.route("/list")
@login_required
def list_tasks():
    family_id = ObjectId(g.user["family_id"])
    tasks = list(db.tasks.find({"family_id": family_id}).sort("due_date", 1))
    return render_template("tasks.html", tasks=tasks)

@tasks_blueprint.route("/create", methods=["GET", "POST"])
@login_required
def create_task():
    family_id = ObjectId(g.user["family_id"])
    family = db.families.find_one({"_id": family_id})
    member_ids = family["members"]
    children = list(db.users.find({"_id": {"$in": member_ids}}))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description", "")
        due_date = request.form.get("due_date", "")
        priority = request.form.get("priority", "medium")
        assigned_to = request.form.get("assigned_to")

        new_task = {
            "family_id": family_id,
            "title": title,
            "description": description,
            "due_date": due_date,
            "status": "incomplete",
            "assigned_to": ObjectId(assigned_to),
            "priority": priority
        }
        db.tasks.insert_one(new_task)
        flash("Task created successfully!")
        return redirect(url_for("tasks.list_tasks"))

    return render_template("create_task.html", children=children)

@tasks_blueprint.route("/edit/<task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    family_id = ObjectId(g.user["family_id"])
    task = db.tasks.find_one({"_id": ObjectId(task_id), "family_id": family_id})
    if not task:
        return "Task not found", 404
    family = db.families.find_one({"_id": family_id})
    children = list(db.users.find({"_id": {"$in": family["members"]}}))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description", "")
        due_date = request.form.get("due_date", "")
        priority = request.form.get("priority", "medium")
        assigned_to = request.form.get("assigned_to")

        update_fields = {
            "title": title,
            "description": description,
            "due_date": due_date,
            "priority": priority,
            "assigned_to": ObjectId(assigned_to)
        }
        db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": update_fields})
        flash("Task updated successfully!")
        return redirect(url_for("tasks.list_tasks"))

    return render_template("edit_task.html", task=task, children=children)

@tasks_blueprint.route("/delete/<task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    family_id = ObjectId(g.user["family_id"])
    result = db.tasks.delete_one({"_id": ObjectId(task_id), "family_id": family_id})
    if result.deleted_count == 1:
        flash("Task deleted successfully!")
    else:
        flash("Task not found or could not be deleted.")
    return redirect(url_for("tasks.list_tasks"))

@tasks_blueprint.route("/complete/<task_id>", methods=["POST"])
@login_required
def complete_task(task_id):
    user_id = ObjectId(g.user["user_id"])
    family_id = ObjectId(g.user["family_id"])
    task = db.tasks.find_one({"_id": ObjectId(task_id), "family_id": family_id})
    if not task:
        return "Task not found", 404
    if task["assigned_to"] != user_id:
        return "You are not assigned to this task", 403

    db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": "complete"}})
    flash("Task marked as complete!")
    return redirect(url_for("tasks.list_tasks"))
