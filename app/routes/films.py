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

    # availability: total copies and available copies (not currently checked out)
    availability_sql = """
    SELECT
      COUNT(i.inventory_id) AS total_copies,
      SUM(CASE WHEN r.rental_id IS NULL THEN 1 ELSE 0 END) AS available_copies
    FROM inventory i
    LEFT JOIN rental r
      ON r.inventory_id = i.inventory_id
     AND r.return_date IS NULL
    WHERE i.film_id = %s;
    """
    avail = query_one(availability_sql, (film_id,))
    film["total_copies"] = int(avail["total_copies"]) if avail and avail["total_copies"] is not None else 0
    film["available_copies"] = int(avail["available_copies"]) if avail and avail["available_copies"] is not None else 0

    return jsonify(film)


@films_bp.get("/api/films/search")
def search_films():
    q = (request.args.get("q") or "").strip()
    mode = (request.args.get("mode") or "any").strip().lower()

    # paging
    try:
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("page_size", "20"))
    except ValueError:
        return jsonify({"error": "page and page_size must be integers"}), 400

    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    offset = (page - 1) * page_size

    if not q:
        return jsonify({"items": [], "page": page, "page_size": page_size, "total": 0, "total_pages": 0})

    like = f"%{q}%"

    # WHERE clause based on mode
    if mode == "title":
        where = "f.title LIKE %s"
        where_params = (like,)
    elif mode == "actor":
        where = "(a.first_name LIKE %s OR a.last_name LIKE %s OR CONCAT(a.first_name,' ',a.last_name) LIKE %s)"
        where_params = (like, like, like)
    elif mode == "genre":
        where = "c.name LIKE %s"
        where_params = (like,)
    else:  # any
        where = """
        (
          f.title LIKE %s
          OR c.name LIKE %s
          OR a.first_name LIKE %s
          OR a.last_name LIKE %s
          OR CONCAT(a.first_name,' ',a.last_name) LIKE %s
        )
        """
        where_params = (like, like, like, like, like)

    # Count total distinct films matching
    count_sql = f"""
    SELECT COUNT(DISTINCT f.film_id) AS total
    FROM film f
    LEFT JOIN film_category fc ON fc.film_id = f.film_id
    LEFT JOIN category c ON c.category_id = fc.category_id
    LEFT JOIN film_actor fa ON fa.film_id = f.film_id
    LEFT JOIN actor a ON a.actor_id = fa.actor_id
    WHERE {where};
    """
    total_row = query_one(count_sql, where_params)
    total = int(total_row["total"]) if total_row and total_row.get("total") is not None else 0
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Page results
    # NOTE: GROUP_CONCAT helps show a preview of matched actors (optional, but nice)
    items_sql = f"""
    SELECT
      f.film_id,
      f.title,
      f.release_year,
      f.rating,
      f.length,
      COALESCE(c.name, '—') AS category,
      GROUP_CONCAT(DISTINCT CONCAT(a.first_name,' ',a.last_name) ORDER BY a.last_name SEPARATOR ', ') AS actors
    FROM film f
    LEFT JOIN film_category fc ON fc.film_id = f.film_id
    LEFT JOIN category c ON c.category_id = fc.category_id
    LEFT JOIN film_actor fa ON fa.film_id = f.film_id
    LEFT JOIN actor a ON a.actor_id = fa.actor_id
    WHERE {where}
    GROUP BY f.film_id, f.title, f.release_year, f.rating, f.length, c.name
    ORDER BY f.title
    LIMIT %s OFFSET %s;
    """
    rows = query_all(items_sql, (*where_params, page_size, offset))

    return jsonify({
        "items": rows,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    })



