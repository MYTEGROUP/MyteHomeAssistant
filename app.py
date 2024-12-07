# app.py (ensure main guard is present at the end)
from bson import ObjectId
from flask import Flask, render_template, g, request, redirect, url_for, session
from dotenv import load_dotenv
import os
import jwt
from src.auth import auth_blueprint
from src.tasks import tasks_blueprint
from src.calendar import calendar_blueprint
from src.budgeting import budgeting_blueprint
from src.meals import meals_blueprint
from src.messaging import messaging_blueprint
from src.family import family_blueprint
from src.utils.db import get_db

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretflaskkey"

app.register_blueprint(auth_blueprint, url_prefix="/auth")
app.register_blueprint(family_blueprint, url_prefix="/family")
app.register_blueprint(tasks_blueprint, url_prefix="/tasks")
app.register_blueprint(calendar_blueprint, url_prefix="/calendar")
app.register_blueprint(budgeting_blueprint, url_prefix="/budget")
app.register_blueprint(meals_blueprint, url_prefix="/meals")
app.register_blueprint(messaging_blueprint, url_prefix="/messages")

JWT_SECRET = os.getenv("JWT_SECRET", "changeme")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
db = get_db()

@app.before_request
def load_user():
    g.user = None
    token = session.get("jwt")
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            g.user = payload
        except jwt.ExpiredSignatureError:
            session.pop("jwt", None)
            return redirect(url_for("auth.login_user"))
        except jwt.InvalidTokenError:
            session.pop("jwt", None)

@app.route("/")
def home():
    if g.user:
        return render_template("index.html", message="Welcome to your Home Management Dashboard!")
    else:
        return render_template("index.html", message="Welcome! Please log in or register.")

@app.route("/dashboard")
def dashboard():
    if not g.user:
        return redirect(url_for("auth.login_user"))

    user_id = ObjectId(g.user["user_id"])
    user = db.users.find_one({"_id": user_id})
    family_id = ObjectId(g.user["family_id"])

    tasks = []
    if user.get("shared_features", {}).get("tasks", True):
        tasks = list(db.tasks.find({"family_id": family_id, "status": "incomplete"}).sort("due_date", 1).limit(5))

    events = list(db.events.find({"family_id": family_id, "visibility": "family"}).sort("date", 1).limit(5))

    messages = []
    if user.get("shared_features", {}).get("meals", True):
        messages = list(db.messages.find({"family_id": family_id}).sort("timestamp", -1).limit(5))
        messages.reverse()

    total_expenses = 0
    if user.get("shared_features", {}).get("budget", True):
        categories = list(db.budget_categories.find({"family_id": family_id}))
        for cat in categories:
            cat_id = cat["_id"]
            cat_expenses = db.expenses.find({"family_id": family_id, "category_id": cat_id})
            cat_total = sum(e["amount"] for e in cat_expenses)
            total_expenses += cat_total
    else:
        categories = []

    meal_plan = None
    if user.get("shared_features", {}).get("meals", True):
        meal_plan = db.meal_plans.find_one({"family_id": family_id}, sort=[("week_start", -1)])

    email_not_verified = not user.get("email_verified", False)

    return render_template("dashboard.html",
                           tasks=tasks,
                           events=events,
                           messages=messages,
                           total_expenses=total_expenses,
                           meal_plan=meal_plan,
                           email_not_verified=email_not_verified)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
