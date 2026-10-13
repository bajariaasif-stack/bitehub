"""Flask routes that connect the browser UI to restaurant data operations."""

import os

# Flask app configuration for the restaurant management system.
from flask import Flask, jsonify, redirect, request, send_file, session

from database import (
    add_menu_item_db,
    add_reservation_db,
    bulk_update_all_menu_photos,
    bulk_update_menu_items,
    create_customer_db,
    create_order_db,
    create_user_db,
    get_customers,
    get_menu_items,
    get_payments,
    get_reservations,
    get_summary,
    init_db,
    update_menu_item_db,
    verify_user_db,
)

# Create the main Flask application and initialize the database when the app starts.
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "restaurant-management-secret")

# Ensure the database tables exist before serving requests.
init_db()


@app.route("/")
def index():
    # Redirect unauthenticated users to the login page.
    if not session.get("user_id"):
        return redirect("/login")
    return send_file("index.html")


@app.route("/login")
def login_page():
    return send_file("login.html")


@app.route("/styles.css")
def styles():
    return send_file("styles.css")


@app.route("/script.js")
def script():
    return send_file("script.js")


@app.route("/api/login", methods=["POST"])
def login_api():
    # Read the submitted login form data and sanitize it.
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    # Check the credentials against the database record.
    user = verify_user_db(username, password)
    if user is None:
        return jsonify({"error": "Invalid username or password."}), 401

    # Store the authenticated user in the session for later requests.
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    return jsonify({"message": "Login successful.", "user": user})


@app.route("/api/register", methods=["POST"])
def register_api():
    # Register a new account using the supplied username, password, and role.
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "Staff User").strip()
    role = (data.get("role") or "staff").strip()

    try:
        user = create_user_db(username, password, full_name=full_name, role=role)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"message": "User created successfully.", "user": user}), 201


@app.route("/api/logout", methods=["POST"])
def logout_api():
    session.clear()
    return jsonify({"message": "Logged out successfully."})


@app.route("/api/menu", methods=["GET", "POST", "PUT"])
def menu_api():
    # GET returns the current menu list; POST adds a new item; PUT updates an existing one.
    if request.method == "GET":
        return jsonify(get_menu_items())

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    category = (data.get("category") or "General").strip()

    try:
        price = float(data.get("price", 0.0))
        stock = int(data.get("stock", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Price and stock must be valid numbers."}), 400

    image_url = (data.get("image_url") or "").strip()

    if not name:
        return jsonify({"error": "Item name is required."}), 400

    if request.method == "PUT":
        item_id = data.get("id")
        try:
            item = update_menu_item_db(item_id, name, category, price, stock, image_url=image_url)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(item)

    try:
        item = add_menu_item_db(name, category, price, stock, image_url=image_url)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(item), 201


@app.route("/api/menu/bulk", methods=["PUT"])
def bulk_menu_api():
    data = request.get_json(silent=True) or {}

    if data.get("apply_to_all") is True:
        image_url = (data.get("image_url") or "").strip()
        try:
            items = bulk_update_all_menu_photos(image_url)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(items)

    items = data.get("items")
    try:
        updated = bulk_update_menu_items(items)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(updated)


@app.route("/api/orders", methods=["POST"])
def create_order():
    # Handle a completed customer order from the frontend.
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        return jsonify({"error": "Please add at least one item to the order before placing it."}), 400

    table_name = data.get("table_name") or "Table 1"
    customer_name = (data.get("customer_name") or "").strip() or "Walk-in Customer"
    customer_phone = (data.get("customer_phone") or "").strip()
    customer_email = (data.get("customer_email") or "").strip()
    customer_address = (data.get("customer_address") or "").strip()
    payment_method = (data.get("payment_method") or "Cash").strip() or "Cash"
    payment_status = (data.get("payment_status") or "pending").strip() or "pending"

    try:
        total = create_order_db(
            items,
            table_name,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            customer_address=customer_address,
            payment_method=payment_method,
            payment_status=payment_status,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "total": float(total),
        "sales": float(get_summary()["sales"]),
        "customer": {"name": customer_name, "phone": customer_phone, "email": customer_email, "address": customer_address},
        "payment_method": payment_method,
        "payment_status": payment_status,
    })


@app.route("/api/customers", methods=["GET", "POST"])
def customers_api():
    # List saved customers or create a new customer record.
    if request.method == "GET":
        return jsonify(get_customers())

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    address = (data.get("address") or "").strip()

    if not name:
        return jsonify({"error": "Customer name is required."}), 400

    try:
        customer = create_customer_db(name, phone=phone, email=email, address=address)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(customer), 201


@app.route("/api/payments")
def payments_api():
    return jsonify(get_payments())


@app.route("/api/summary")
def summary():
    return jsonify(get_summary())


@app.route("/api/reservations", methods=["GET", "POST"])
def reservations_api():
    # Return reservations or add a new table booking.
    if request.method == "GET":
        return jsonify(get_reservations())

    data = request.get_json(silent=True) or {}
    guest_name = (data.get("guest_name") or "").strip()
    reservation_date = (data.get("reservation_date") or "").strip()
    reservation_time = (data.get("reservation_time") or "").strip()
    guests = data.get("guests")

    if not guest_name or not reservation_date or not reservation_time:
        return jsonify({"error": "Guest name, date, and time are required."}), 400

    try:
        guests = int(guests)
    except (TypeError, ValueError):
        return jsonify({"error": "Guest count must be a number."}), 400

    reservation = add_reservation_db(guest_name, reservation_date, reservation_time, guests)
    return jsonify(reservation), 201


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False, host="0.0.0.0", port=5000)

