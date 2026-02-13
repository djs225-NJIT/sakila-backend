from flask import Blueprint, jsonify
from app.db import query_one

health_bp = Blueprint("health", __name__)

@health_bp.get("/api/health")
def health():
    row = query_one("SELECT 1 as db_ok;")
    return jsonify({"status": "ok"})