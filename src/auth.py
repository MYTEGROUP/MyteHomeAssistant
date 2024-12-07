# Step 4: src/auth.py (no explanations, final integrated code)
from datetime import datetime, timedelta
import jwt
import os
import secrets
from flask import Blueprint, request, render_template, redirect, url_for, session, flash, g
from pymongo import MongoClient
from passlib.context import CryptContext
from src.utils.mailer import send_email
from bson.objectid import ObjectId
from src.utils.db import get_db

auth_blueprint = Blueprint("auth", __name__)
db = get_db()
JWT_SECRET = os.getenv("JWT_SECRET", "changeme")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@auth_blueprint.route("/register", methods=["GET", "POST"])
def register_user():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        family_invite = request.form.get("family_invite")
        name = request.form.get("name", email)

        if not email or not password:
            return render_template("register.html", error="Email and password required")

        existing = db.users.find_one({"email": email})
        if existing:
            return render_template("register.html", error="Email already registered")

        hashed_pw = pwd_context.hash(password)

        if family_invite:
            family = db.families.find_one({"invite_code": family_invite})
            if not family:
                return render_template("register.html", error="Invalid family invite code.")
            family_id = family["_id"]
        else:
            family_id = db.families.insert_one({
                "name": f"{name}'s Family",
                "invite_code": str(ObjectId()),
                "members": []
            }).inserted_id

        new_user = {
            "email": email,
            "hashed_password": hashed_pw,
            "family_id": family_id,
            "name": name,
            "shared_features": {
                "tasks": True,
                "meals": True,
                "budget": True
            },
            "dietary_preferences": {
                "restrictions": [],
                "likes": [],
                "dislikes": []
            }
        }

        user_id = db.users.insert_one(new_user).inserted_id
        db.families.update_one({"_id": family_id}, {"$push": {"members": user_id}})

        verification_token = secrets.token_urlsafe(32)
        db.users.update_one({"_id": user_id}, {"$set": {
            "email_verified": False,
            "email_verification_token": verification_token
        }})

        verify_url = url_for("auth.verify_email", token=verification_token, _external=True)
        email_body = f"Welcome to Myte Home Assistant!\n\nPlease verify your email by clicking this link: {verify_url}"
        send_email(email, "Verify your email - Myte Home Assistant", email_body)
        flash("Registration successful! Please check your email for a verification link.")
        return redirect(url_for("auth.login_user"))

    return render_template("register.html")

@auth_blueprint.route("/login", methods=["GET", "POST"])
def login_user():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = db.users.find_one({"email": email})
        if not user or not pwd_context.verify(password, user["hashed_password"]):
            return render_template("login.html", error="Invalid credentials")

        payload = {
            "sub": user["email"],
            "user_id": str(user["_id"]),
            "family_id": str(user["family_id"]),
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        access_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        session["jwt"] = access_token
        return redirect(url_for("home"))

    return render_template("login.html")

@auth_blueprint.route("/logout")
def logout_user():
    session.pop("jwt", None)
    return redirect(url_for("auth.login_user"))

@auth_blueprint.route("/verify_email/<token>")
def verify_email(token):
    user = db.users.find_one({"email_verification_token": token})
    if user:
        db.users.update_one({"_id": user["_id"]}, {"$set": {"email_verified": True}, "$unset": {"email_verification_token": ""}})
        flash("Your email is now verified! You can enjoy full features.")
        return redirect(url_for("home"))
    else:
        flash("Invalid or expired verification link.")
        return redirect(url_for("home"))

@auth_blueprint.route("/resend_verification")
def resend_verification():
    if not g.user:
        return redirect(url_for("auth.login_user"))
    user = db.users.find_one({"_id": ObjectId(g.user["user_id"])})
    if user.get("email_verified", False):
        flash("Your email is already verified.")
        return redirect(url_for("home"))
    new_token = secrets.token_urlsafe(32)
    db.users.update_one({"_id": user["_id"]}, {"$set": {"email_verification_token": new_token}})
    verify_url = url_for("auth.verify_email", token=new_token, _external=True)
    email_body = f"Please verify your email: {verify_url}"
    send_email(user["email"], "Resend: Verify your email", email_body)
    flash("Verification email resent!")
    return redirect(url_for("home"))

@auth_blueprint.route("/request_password_reset", methods=["GET", "POST"])
def request_password_reset():
    if request.method == "POST":
        email = request.form.get("email")
        user = db.users.find_one({"email": email})
        if user:
            reset_token = secrets.token_urlsafe(32)
            expires = datetime.utcnow() + timedelta(hours=1)
            db.users.update_one({"_id": user["_id"]}, {"$set": {
                "password_reset_token": reset_token,
                "password_reset_expires": expires
            }})
            reset_url = url_for("auth.reset_password", token=reset_token, _external=True)
            email_body = f"Reset your password by clicking here: {reset_url}\nIf you didn't request this, ignore."
            send_email(user["email"], "Password Reset - Myte Home Assistant", email_body)
        flash("If that email exists, a reset link has been sent.")
        return redirect(url_for("auth.login_user"))
    return render_template("request_password_reset.html")

@auth_blueprint.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = db.users.find_one({"password_reset_token": token})
    if not user:
        flash("Invalid token.")
        return redirect(url_for("auth.login_user"))
    if user["password_reset_expires"] < datetime.utcnow():
        flash("Token expired.")
        return redirect(url_for("auth.request_password_reset"))
    if request.method == "POST":
        new_password = request.form.get("password")
        hashed = pwd_context.hash(new_password)
        db.users.update_one({"_id": user["_id"]}, {"$set": {"hashed_password": hashed}, "$unset": {"password_reset_token": "", "password_reset_expires": ""}})
        flash("Password reset successful! You can log in now.")
        return redirect(url_for("auth.login_user"))
    return render_template("reset_password.html")
