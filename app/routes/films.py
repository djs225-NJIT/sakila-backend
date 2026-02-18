from flask import Blueprint, jsonify, request
from app.db import query_all

films_bp = Blueprint("films", __name__)

@films_bp.get("/api/films/top-rented")
def top_rented_films():
    # default limit=5, clamp 1..50

    
    limit_str = request.args.get("limit", "5")
    try:
        limit = int(limit_str)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    if limit < 1 or limit > 50:
        return jsonify({"error": "limit must be between 1 and 50"}), 400
    

    sql = """
    SELECT 
        i.film_id AS film_id,
        f.title AS title,
        c.name AS category,
        COUNT(*) AS rented
        FROM rental r
        LEFT JOIN inventory i ON r.inventory_id = i.inventory_id
        LEFT JOIN film f ON i.film_id = f.film_id 
        LEFT JOIN film_category fc ON f.film_id = fc.film_id 
        LEFT JOIN category c ON fc.category_id = c.category_id 
        GROUP BY i.film_id, f.title, c.name
        ORDER BY rented DESC
        LIMIT %s;
    """
    # rows = query_all(sql, (limit))
    rows = query_all(sql, (limit,))
    return jsonify(rows)
    #return jsonify({"count": len(rows), "results": rows})