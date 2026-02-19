from flask import Blueprint, jsonify, request
from app.db import query_all, query_one

actors_bp = Blueprint("actors", __name__)


@actors_bp.get("/api/actors/top")
def top_actors():
    limit_str = request.args.get("limit", "5")
    try:
        limit = int(limit_str)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    if limit < 1 or limit > 50:
        return jsonify({"error": "limit must be between 1 and 50"}), 400

    sql = """
    SELECT
        a.actor_id,
        a.first_name,
        a.last_name,
        COUNT(DISTINCT fa.film_id) AS film_count
        FROM actor a
        JOIN film_actor fa ON fa.actor_id = a.actor_id
        GROUP BY a.actor_id, a.first_name, a.last_name
        ORDER BY film_count DESC, a.last_name, a.first_name
        LIMIT %s;
    """
    rows = query_all(sql, (limit,))
    return jsonify(rows)


@actors_bp.get("/api/actors/<int:actor_id>")
def actor_details(actor_id: int):
    actor_sql = """
    SELECT actor_id, first_name, last_name, last_update
        FROM actor
        WHERE actor_id = %s;
    """
    actor = query_one(actor_sql, (actor_id,))
    if actor is None:
        return jsonify({"error": "Actor not found"}), 404

    counts_sql = """
    SELECT
        COUNT(DISTINCT fa.film_id) AS film_count,
        COUNT(r.rental_id) AS total_rentals
        FROM film_actor fa
        LEFT JOIN inventory i ON i.film_id = fa.film_id
        LEFT JOIN rental r ON r.inventory_id = i.inventory_id
        WHERE fa.actor_id = %s;
    """
    counts = query_one(counts_sql, (actor_id,))
    actor["film_count"] = counts["film_count"]
    actor["total_rentals"] = counts["total_rentals"]

    films_sql = """
    SELECT
        f.film_id,
        f.title,
        c.name AS category,
        COUNT(r.rental_id) AS rented
    FROM film_actor fa
    JOIN film f ON f.film_id = fa.film_id
    LEFT JOIN film_category fc ON fc.film_id = f.film_id
    LEFT JOIN category c ON c.category_id = fc.category_id
    JOIN inventory i ON i.film_id = f.film_id
    JOIN rental r ON r.inventory_id = i.inventory_id
    WHERE fa.actor_id = %s
    GROUP BY f.film_id, f.title, c.name
    ORDER BY rented DESC
    LIMIT 5;
    """
    actor["top_films"] = query_all(films_sql, (actor_id,))
    return jsonify(actor)