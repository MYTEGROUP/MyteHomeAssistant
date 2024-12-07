# src/utils/security.py
from functools import wraps
from flask import g, redirect, url_for

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth.login_user"))
        return f(*args, **kwargs)
    return wrapper
