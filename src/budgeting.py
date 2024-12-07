# Step 7: src/budgeting.py (no explanations)
from flask import Blueprint, g, redirect, url_for, render_template, request, flash
from bson.objectid import ObjectId
from src.utils.db import get_db
from datetime import datetime

budgeting_blueprint = Blueprint("budgeting", __name__)
db = get_db()

def login_required(f):
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth.login_user"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@budgeting_blueprint.route("/")
@login_required
def budgeting_home():
    family_id = ObjectId(g.user["family_id"])
    categories = list(db.budget_categories.find({"family_id": family_id}))
    total_expenses = 0
    category_sums = {}
    for cat in categories:
        cat_id = cat["_id"]
        cat_expenses = db.expenses.find({"family_id": family_id, "category_id": cat_id})
        cat_total = sum(e["amount"] for e in cat_expenses)
        category_sums[str(cat_id)] = {"name": cat["name"], "total": cat_total, "limit": cat["limit"]}
        total_expenses += cat_total

    return render_template("budget_home.html", categories=categories, category_sums=category_sums, total=total_expenses)

@budgeting_blueprint.route("/add_category", methods=["GET","POST"])
@login_required
def add_category():
    if request.method == "POST":
        family_id = ObjectId(g.user["family_id"])
        name = request.form.get("name")
        limit = float(request.form.get("limit", 0))
        db.budget_categories.insert_one({"family_id": family_id, "name": name, "limit": limit})
        flash("Category added!")
        return redirect(url_for("budgeting.budgeting_home"))
    return render_template("add_category.html")

@budgeting_blueprint.route("/add_expense", methods=["GET","POST"])
@login_required
def add_expense():
    family_id = ObjectId(g.user["family_id"])
    categories = list(db.budget_categories.find({"family_id": family_id}))
    if not categories:
        flash("Please create a category first.")
        return redirect(url_for("budgeting.add_category"))
    if request.method == "POST":
        category_id = request.form.get("category_id")
        amount = float(request.form.get("amount"))
        date = request.form.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
        description = request.form.get("description", "")
        db.expenses.insert_one({
            "family_id": family_id,
            "category_id": ObjectId(category_id),
            "amount": amount,
            "date": date,
            "description": description
        })
        flash("Expense added!")
        return redirect(url_for("budgeting.budgeting_home"))

    return render_template("add_expense.html", categories=categories)
