from flask import Blueprint, jsonify, request
from app.db import query_all, query_one, execute_write

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

    # get customer rentals
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


@customers_bp.put("/api/customers/<int:customer_id>")
def update_customer(customer_id):
    body = request.json

    if body is None:
        return jsonify({"error": "request body required"}), 400

    first_name = body.get("first_name")
    last_name = body.get("last_name")
    email = body.get("email")
    active = body.get("active")

    # confirm customer exists
    customer = query_one(
        "SELECT customer_id FROM customer WHERE customer_id = %s",
        (customer_id,)
    )

    
    if not customer:
        return jsonify({"error": "customer not found"}), 404

    # require at least one field
    if first_name is None and last_name is None and email is None and active is None:
        return jsonify({"error": "no fields provided"}), 400

    execute_write(
        """
        UPDATE customer
        SET
            first_name = COALESCE(%s, first_name),
            last_name = COALESCE(%s, last_name),
            email = COALESCE(%s, email),
            active = COALESCE(%s, active)
        WHERE customer_id = %s
        """,
        (first_name, last_name, email, active, customer_id)
    )

    updated = query_one(
        """
        SELECT customer_id, first_name, last_name, email, active, create_date
        FROM customer
        WHERE customer_id = %s
        """,
        (customer_id,)
    )

    return jsonify(updated)


@customers_bp.delete("/api/customers/<int:customer_id>")
def delete_customer(customer_id):

    customer = query_one(
        "SELECT customer_id FROM customer WHERE customer_id = %s",
        (customer_id,)
    )

    if not customer:
        return jsonify({"error": "customer not found"}), 404

    # set active to 0 instead of deleting
    execute_write(
        """
        UPDATE customer
        SET active = 0
        WHERE customer_id = %s
        """,
        (customer_id,)
    )

    return jsonify({"message": "customer deactivated"})

@customers_bp.post("/api/customers")
def create_customer():
    body = request.json

    if body is None:
        return jsonify({"error": "request body required"}), 400

    first_name = body.get("first_name")
    last_name = body.get("last_name")
    email = body.get("email")
    store_id = body.get("store_id")
    address_id = body.get("address_id")

    # required fields
    if not first_name or not last_name or not email or store_id is None or address_id is None:
        return jsonify({"error": "All fields required"}), 400

    # validate ids
    try:
        store_id = int(store_id)
        address_id = int(address_id)
    except (TypeError, ValueError):
        return jsonify({"error": "store_id and address_id must be integers"}), 400

    # confirm store exists
    store = query_one("SELECT store_id FROM store WHERE store_id = %s", (store_id,))
    if not store:
        return jsonify({"error": "store not found"}), 404

    # confirm address exists
    address = query_one("SELECT address_id FROM address WHERE address_id = %s", (address_id,))
    if not address:
        return jsonify({"error": "address not found"}), 404

    new_customer_id = execute_write(
        """
        INSERT INTO customer (store_id, first_name, last_name, email, address_id, active, create_date, last_update)
        VALUES (%s, %s, %s, %s, %s, 1, NOW(), NOW())
        """,
        (store_id, first_name, last_name, email, address_id),
    )

    created = query_one(
        """
        SELECT customer_id, first_name, last_name, email, active, create_date
        FROM customer
        WHERE customer_id = %s
        """,
        (new_customer_id,),
    )

    return jsonify(created), 201