from flask import Blueprint, jsonify, request
from app.db import query_all, query_one

customers_bp = Blueprint("customers", __name__)

@customers_bp.get("/api/customers")
def list_customers():
    customer_id = request.args.get("customer_id")
    first_name = request.args.get("first_name")
    last_name = request.args.get("last_name")

    page = request.args.get("page", 1, type=int)
    per_page = 20

    filters = [customer_id, first_name, last_name]
    provided_count = sum(1 for f in filters if f)
    if provided_count > 1:
        return jsonify({
            "error": "Provide only one of customer_id, first_name, or last_name"
        }), 400

    where_clause = ""
    where_params = ()

    if customer_id:
        try:
            cid = int(customer_id)
        except ValueError:
            return jsonify({"error": "customer_id must be an integer"}), 400
        where_clause = "WHERE customer_id = %s"
        where_params = (cid,)

    elif first_name:
        where_clause = "WHERE first_name LIKE %s"
        where_params = (f"%{first_name}%",)

    elif last_name:
        where_clause = "WHERE last_name LIKE %s"
        where_params = (f"%{last_name}%",)

    total_row = query_one(
        f"SELECT COUNT(*) AS total FROM customer {where_clause}",
        where_params
    )
    total = total_row["total"] if total_row else 0
    total_pages = (total + per_page - 1) // per_page

    if total_pages == 0:
        return jsonify({
            "page": 1,
            "per_page": per_page,
            "total_customers": 0,
            "total_pages": 0,
            "items": []
        })

    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start = (page - 1) * per_page

    rows = query_all(
        f"""
        SELECT customer_id, first_name, last_name
        FROM customer
        {where_clause}
        ORDER BY customer_id
        LIMIT %s OFFSET %s
        """,
        where_params + (per_page, start),
    )

    return jsonify({
        "page": page,
        "per_page": per_page,
        "total_customers": total,
        "total_pages": total_pages,
        "items": rows
    })


@customers_bp.get("/api/customers/<int:customer_id>")
def customer_details(customer_id):
    customer = query_one(
        """
        SELECT customer_id, first_name, last_name, email, active, create_date
        FROM customer
        WHERE customer_id = %s
        """,
        (customer_id,)
    )

    if not customer:
        return jsonify({"error": "customer not found"}), 404

    rentals = query_all(
        """
        SELECT r.rental_id, r.rental_date, r.return_date, f.film_id, f.title
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        WHERE r.customer_id = %s
        ORDER BY r.rental_date DESC
        """,
        (customer_id,)
    )

    return jsonify({
        "customer": customer,
        "rentals": rentals
    })
