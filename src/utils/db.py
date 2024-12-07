# src/utils/db.py
import os
from pymongo import MongoClient

_client = None

def get_db():
    global _client
    if not _client:
        MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        _client = MongoClient(MONGODB_URI)
    return _client["home_management_db"]
