# src/meals.py (updated to add image generation after meal plan creation and actual audio upload route)
from flask import Blueprint, g, redirect, url_for, render_template, request, flash
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from src.utils.db import get_db
from src.utils.openai_client import generate_meals, generate_image, transcribe_audio
import json

meals_blueprint = Blueprint("meals", __name__)
db = get_db()

def login_required(f):
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth.login_user"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@meals_blueprint.route("/")
@login_required
def meals_home():
    family_id = ObjectId(g.user["family_id"])
    plan = db.meal_plans.find_one({"family_id": family_id}, sort=[("week_start", -1)])
    grocery = db.grocery_list.find_one({"family_id": family_id})
    items = grocery["items"] if grocery else []
    return render_template("meals_home.html", plan=plan, items=items)

@meals_blueprint.route("/create_plan", methods=["GET","POST"])
@login_required
def create_plan():
    if request.method == "POST":
        family_id = ObjectId(g.user["family_id"])
        week_start = request.form.get("week_start")
        meals = []
        for day in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]:
            meal_name = request.form.get(f"meal_{day.lower()}", "")
            servings = request.form.get(f"servings_{day.lower()}", 4)
            meals.append({"day": day, "name": meal_name, "servings": int(servings)})
        db.meal_plans.insert_one({"family_id": family_id, "week_start": week_start, "meals": meals})
        flash("Meal plan created!")
        return redirect(url_for("meals.meals_home"))
    return render_template("create_plan.html")

@meals_blueprint.route("/generate_grocery", methods=["POST"])
@login_required
def generate_grocery():
    flash("Grocery list generated! (Mocked)")
    family_id = ObjectId(g.user["family_id"])
    db.grocery_list.update_one({"family_id": family_id}, {"$set": {"items": []}}, upsert=True)
    return redirect(url_for("meals.meals_home"))

@meals_blueprint.route("/add_grocery_item", methods=["POST"])
@login_required
def add_grocery_item():
    family_id = ObjectId(g.user["family_id"])
    name = request.form.get("item_name")
    quantity = request.form.get("quantity")
    db.grocery_list.update_one({"family_id": family_id}, {"$push": {"items": {"name": name, "quantity": quantity, "added_by": ObjectId(g.user["user_id"])}}}, upsert=True)
    flash("Item added to grocery list!")
    return redirect(url_for("meals.meals_home"))

@meals_blueprint.route("/remove_grocery_item/<int:index>", methods=["POST"])
@login_required
def remove_grocery_item(index):
    family_id = ObjectId(g.user["family_id"])
    grocery = db.grocery_list.find_one({"family_id": family_id})
    if grocery and 0 <= index < len(grocery["items"]):
        items = grocery["items"]
        del items[index]
        db.grocery_list.update_one({"family_id": family_id}, {"$set": {"items": items}})
        flash("Item removed from grocery list!")
    return redirect(url_for("meals.meals_home"))

@meals_blueprint.route("/preferences/voice-input", methods=["POST"])
@login_required
def voice_input():
    transcription = request.form.get("transcription", "")
    user_id = ObjectId(g.user["user_id"])
    user = db.users.find_one({"_id": user_id})
    likes = user.get("dietary_preferences", {}).get("likes", [])
    dislikes = user.get("dietary_preferences", {}).get("dislikes", [])
    if "salmon" not in likes:
        likes.append("salmon")
    if "mushrooms" not in dislikes:
        dislikes.append("mushrooms")
    db.users.update_one({"_id": user_id}, {"$set": {
        "dietary_preferences.likes": likes,
        "dietary_preferences.dislikes": dislikes
    }})
    flash("Preferences updated from voice input!")
    return redirect(url_for("meals.meals_home"))

@meals_blueprint.route("/preferences/voice-input-audio", methods=["POST"])
@login_required
def voice_input_audio():
    if 'audio' not in request.files:
        flash("No audio file provided.")
        return redirect(url_for("meals.meals_home"))
    audio_file = request.files['audio']
    if audio_file.filename == '':
        flash("No selected file.")
        return redirect(url_for("meals.meals_home"))
    filename = secure_filename(audio_file.filename)
    audio_path = os.path.join(UPLOAD_FOLDER, filename)
    audio_file.save(audio_path)
    transcript = transcribe_audio(audio_path)
    # Parse transcript for preferences (simple example)
    user_id = ObjectId(g.user["user_id"])
    user = db.users.find_one({"_id": user_id})
    likes = user.get("dietary_preferences", {}).get("likes", [])
    dislikes = user.get("dietary_preferences", {}).get("dislikes", [])

    # Example: If transcript contains "I like broccoli"
    if "broccoli" in transcript.lower() and "like" in transcript.lower():
        if "broccoli" not in likes:
            likes.append("broccoli")
    # Example: If transcript contains "I hate onions"
    if "onions" in transcript.lower() and ("hate" in transcript.lower() or "dislike" in transcript.lower()):
        if "onions" not in dislikes:
            dislikes.append("onions")

    db.users.update_one({"_id": user_id}, {"$set": {
        "dietary_preferences.likes": likes,
        "dietary_preferences.dislikes": dislikes
    }})

    flash("Preferences updated from audio input!")
    return redirect(url_for("meals.meals_home"))

@meals_blueprint.route("/generate", methods=["POST"])
@login_required
def generate_meal_plan():
    family_id = ObjectId(g.user["family_id"])
    family = db.families.find_one({"_id": family_id})
    members = db.users.find({"_id": {"$in": family["members"]}})
    restrictions = set()
    likes = set()
    dislikes = set()
    for m in members:
        prefs = m.get("dietary_preferences", {})
        for r in prefs.get("restrictions", []):
            restrictions.add(r)
        for l in prefs.get("likes", []):
            likes.add(l)
        for d in prefs.get("dislikes", []):
            dislikes.add(d)

    family_preferences = {
        "dietary_restrictions": list(restrictions),
        "common_likes": list(likes),
        "common_dislikes": list(dislikes),
        "servings": len(family["members"])
    }

    meal_plan_json = generate_meals(family_preferences)
    try:
        meal_plan = json.loads(meal_plan_json)
    except:
        flash("Could not parse meal plan. Please try again.")
        return redirect(url_for("meals.meals_home"))

    # Add images to each meal
    for meal in meal_plan.get("meals", []):
        desc = meal.get("description", "")
        image_url = generate_image(meal["name"], desc)
        meal["image_url"] = image_url

    meal_plan["family_id"] = family_id
    db.meal_plans.insert_one(meal_plan)
    flash("Meal plan generated with images!")
    return redirect(url_for("meals.meals_home"))

@meals_blueprint.route("/details/<day>", methods=["GET"])
@login_required
def meal_details(day):
    family_id = ObjectId(g.user["family_id"])
    plan = db.meal_plans.find_one({"family_id": family_id}, sort=[("week_start", -1)])
    if not plan:
        flash("No meal plan found")
        return redirect(url_for("meals.meals_home"))
    meal = next((m for m in plan["meals"] if m["day"].lower() == day.lower()), None)
    if not meal:
        flash("Meal not found for this day.")
        return redirect(url_for("meals.meals_home"))
    return render_template("meal_details.html", meal=meal)
