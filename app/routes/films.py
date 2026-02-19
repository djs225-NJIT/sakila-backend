from flask import Blueprint, jsonify, request
from app.db import query_all, query_one

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


@films_bp.get("/api/films/<int:film_id>")
def film_details(film_id: int):
    film_sql = """
    SELECT
        f.film_id,
        f.title,
        f.description,
        f.release_year,
        f.rating,
        f.length,
        c.name AS category
    FROM film f
    LEFT JOIN film_category fc ON fc.film_id = f.film_id
    LEFT JOIN category c ON c.category_id = fc.category_id
    WHERE f.film_id = %s;
    """
    film = query_one(film_sql, (film_id,))
    if film is None:
        return jsonify({"error": "Film not found"}), 404

    actors_sql = """
    SELECT
        a.actor_id,
        a.first_name,
        a.last_name
    FROM film_actor fa
    JOIN actor a ON a.actor_id = fa.actor_id
    WHERE fa.film_id = %s
    ORDER BY a.last_name, a.first_name;
    """
    film["actors"] = query_all(actors_sql, (film_id,))
    return jsonify(film)





