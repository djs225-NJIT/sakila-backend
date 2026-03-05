from flask import Blueprint, jsonify, request
from app.db import query_one, query_all, execute_write

rentals_bp = Blueprint("rentals", __name__)

@rentals_bp.post("/api/rentals")
def create_rental():
    body = request.get_json(silent=True) or {}

    film_id = body.get("film_id")
    customer_id = body.get("customer_id")
    staff_id = body.get("staff_id", 1)
    store_id = body.get("store_id")  # optional

    # basic validation
    try:
        film_id = int(film_id)
        customer_id = int(customer_id)
        staff_id = int(staff_id)
        store_id = int(store_id) if store_id is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "film_id, customer_id, staff_id, store_id must be integers"}), 400

    # confirm customer exists
    customer = query_one("SELECT customer_id FROM customer WHERE customer_id = %s;", (customer_id,))
    if customer is None:
        return jsonify({"error": "Customer not found"}), 404

    # confirm staff exists (and store if provided)
    staff = query_one("SELECT staff_id, store_id FROM staff WHERE staff_id = %s;", (staff_id,))
    if staff is None:
        return jsonify({"error": "Staff not found"}), 404

    # If store_id not provided, default to staff's store_id
    if store_id is None:
        store_id = int(staff["store_id"])

    store = query_one("SELECT store_id FROM store WHERE store_id = %s;", (store_id,))
    if store is None:
        return jsonify({"error": "Store not found"}), 404

    # find an available inventory copy at that store:
    # available means: no active rental (return_date IS NULL)
    inv_sql = """
    SELECT i.inventory_id
    FROM inventory i
    LEFT JOIN rental r
      ON r.inventory_id = i.inventory_id
     AND r.return_date IS NULL
    WHERE i.film_id = %s
      AND i.store_id = %s
      AND r.rental_id IS NULL
    ORDER BY i.inventory_id
    LIMIT 1;
    """
    inv = query_one(inv_sql, (film_id, store_id))
    if inv is None:
        return jsonify({"error": "No available copies to rent for this film (at that store)"}), 409

    inventory_id = int(inv["inventory_id"])

    # create rental
    insert_sql = """
    INSERT INTO rental (rental_date, inventory_id, customer_id, return_date, staff_id, last_update)
    VALUES (NOW(), %s, %s, NULL, %s, NOW());
    """
    # If your query_one/query_all wrappers don't support returning lastrowid,
    # we can fetch the created row by selecting the newest rental for that inv/customer.
    rental_id = execute_write(insert_sql, (inventory_id, customer_id, staff_id))

    created = query_one(
        """
        SELECT rental_id, rental_date, inventory_id, customer_id, return_date, staff_id, last_update
        FROM rental
        WHERE rental_id = %s
        """,
        (rental_id,)
    )

    return jsonify({
        "message": "Rental created",
        "rental": created
    }), 201

@rentals_bp.patch("/api/rentals/<int:rental_id>/return")
def return_movie(rental_id):

    # check rental exists
    rental = query_one(
        """
        SELECT rental_id, return_date
        FROM rental
        WHERE rental_id = %s
        """,
        (rental_id,)
    )

    if not rental:
        return jsonify({"error": "rental not found"}), 404

    # can't return twice
    if rental["return_date"] is not None:
        return jsonify({"error": "movie already returned"}), 400

    execute_write(
        """
        UPDATE rental
        SET return_date = NOW()
        WHERE rental_id = %s
        """,
        (rental_id,)
    )

    updated = query_one(
        """
        SELECT rental_id, rental_date, return_date
        FROM rental
        WHERE rental_id = %s
        """,
        (rental_id,)
    )

    return jsonify(updated)