"""Database connections and persistence helpers for restaurant records."""

import base64
import os
import re
import sqlite3
from datetime import date, datetime, time
from urllib.parse import quote
from urllib.request import urlopen

from werkzeug.security import check_password_hash, generate_password_hash

# Database file location for the restaurant application.
DB_PATH = os.path.join(os.path.dirname(__file__), "restaurant.db")


# Adapt MySQL results to the row behavior used by the SQLite queries below.
class MySQLRow(dict):
    def __init__(self, values):
        super().__init__(
            (key, value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat() if isinstance(value, (date, time)) else value)
            for key, value in values.items()
        )

    def __getitem__(self, key):
        if isinstance(key, int):
            key = tuple(self.keys())[key]
        return super().__getitem__(key)


class MySQLCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def fetchone(self):
        row = self._cursor.fetchone()
        return MySQLRow(row) if row is not None else None

    def fetchall(self):
        return [MySQLRow(row) for row in self._cursor.fetchall()]


class MySQLConnection:
    def __init__(self, connection):
        self._connection = connection

    def execute(self, query, params=()):
        pragma_match = re.fullmatch(r"\s*PRAGMA\s+table_info\((\w+)\)\s*", query, re.IGNORECASE)
        if pragma_match:
            query = (
                "SELECT ORDINAL_POSITION AS cid, COLUMN_NAME AS name "
                "FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                "ORDER BY ORDINAL_POSITION"
            )
            params = (pragma_match.group(1),)
        elif query.lstrip().upper().startswith(("CREATE TABLE", "ALTER TABLE")):
            query = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGINT PRIMARY KEY AUTO_INCREMENT")
            query = re.sub(r"\bINTEGER\b", "BIGINT", query, flags=re.IGNORECASE)
            query = re.sub(r"\bREAL\b", "DOUBLE", query, flags=re.IGNORECASE)
            query = re.sub(r"image_url\s+TEXT\s+DEFAULT\s+''", "image_url LONGTEXT NULL", query, flags=re.IGNORECASE)
            query = re.sub(r"created_at\s+TEXT\s+DEFAULT\s+CURRENT_TIMESTAMP", "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP", query, flags=re.IGNORECASE)
            query = re.sub(r"\bTEXT\s+NOT NULL\s+UNIQUE\b", "VARCHAR(255) NOT NULL UNIQUE", query, flags=re.IGNORECASE)
            query = re.sub(r"\bTEXT\s+NOT NULL\b", "VARCHAR(255) NOT NULL", query, flags=re.IGNORECASE)
            query = re.sub(r"\bTEXT\s+DEFAULT\s+''", "VARCHAR(2048) DEFAULT ''", query, flags=re.IGNORECASE)
            query = re.sub(r"\bTEXT\b", "LONGTEXT", query, flags=re.IGNORECASE)
            if query.lstrip().upper().startswith("CREATE TABLE"):
                query = query.rstrip() + " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

        cursor = self._connection.cursor()
        cursor.execute(query.replace("?", "%s"), params)
        return MySQLCursor(cursor)

    def commit(self):
        self._connection.commit()

    def close(self):
        self._connection.close()


# Fetch usable dish art, falling back to generated artwork when a URL fails.
def real_photo_data_uri(url, label="Dish", accent="#ff7b54", background="#fff4e8"):
    try:
        with urlopen(url, timeout=20) as response:
            content_type = response.headers.get_content_type()
            if not content_type.startswith("image/"):
                raise ValueError("Not an image URL")
            payload = response.read()
        encoded = base64.b64encode(payload).decode("ascii")
        return f"data:{content_type};base64,{encoded}"
    except Exception:
        return svg_data_uri(label, accent=accent, background=background)


def svg_data_uri(label, accent="#ff7b54", background="#fff4e8"):
    safe_label = (
        str(label)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    icon_map = {
        "Roti": "<path d='M155 246C186 205 234 179 300 177C366 175 414 205 445 246C482 294 452 338 389 346C342 352 288 348 241 349C178 350 124 319 155 246Z' fill='rgba(255,255,255,0.54)'/>",
        "Chapati": "<path d='M150 245C175 204 225 170 301 172C382 174 433 214 448 252C431 313 385 340 301 342C213 344 167 308 150 245Z' fill='rgba(255,255,255,0.50)'/>",
        "Paratha": "<path d='M138 240C168 190 229 155 300 156C382 157 440 196 460 247C431 318 382 344 300 346C215 348 168 319 138 240Z' fill='rgba(255,255,255,0.55)'/>",
        "Dal": "<path d='M125 248C172 178 237 160 299 160C375 160 442 196 465 245C437 330 370 344 298 349C222 353 162 325 125 248Z' fill='rgba(255,255,255,0.58)'/>",
        "Chawal": "<path d='M120 244C170 182 227 158 300 159C371 160 437 187 467 242C435 325 363 346 299 347C227 349 169 321 120 244Z' fill='rgba(255,255,255,0.62)'/>",
        "Dal Chawal": "<path d='M111 241C162 189 213 170 300 170C380 170 436 188 483 241C454 321 382 346 299 349C227 350 167 323 111 241Z' fill='rgba(255,255,255,0.60)'/>",
        "Buttermilk": "<path d='M188 150H412C437 150 456 170 456 196V250C456 323 398 366 300 366C201 366 144 323 144 250V196C144 170 163 150 188 150Z' fill='rgba(255,255,255,0.60)'/>",
    }
    icon = icon_map.get(label, "<circle cx='300' cy='220' r='120' fill='rgba(255,255,255,0.52)'/>")
    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 420'>
      <defs>
        <linearGradient id='g' x1='0' x2='1'>
          <stop offset='0%' stop-color='{background}'/>
          <stop offset='100%' stop-color='{accent}'/>
        </linearGradient>
      </defs>
      <rect width='600' height='420' rx='32' fill='url(#g)'/>
      <circle cx='500' cy='88' r='52' fill='rgba(255,255,255,0.24)'/>
      <path d='M88 304C163 246 218 224 302 228C383 232 434 253 513 304' stroke='rgba(255,255,255,0.46)' stroke-width='16' fill='none' stroke-linecap='round'/>
      <ellipse cx='300' cy='235' rx='170' ry='110' fill='rgba(255,255,255,0.16)'/>
      {icon}
      <ellipse cx='300' cy='248' rx='150' ry='66' fill='rgba(255,255,255,0.18)'/>
      <text x='300' y='220' text-anchor='middle' font-size='52' font-family='Arial, sans-serif' font-weight='700' fill='#1f2937'>{safe_label}</text>
      <text x='300' y='295' text-anchor='middle' font-size='22' font-family='Arial, sans-serif' fill='#334155'>BiteHub</text>
    </svg>
    """.strip()
    return f"data:image/svg+xml;charset=utf-8,{quote(svg)}"


def dish_palette(name):
    palettes = {
        "Roti": ("#d97706", "#fff7ed"),
        "Chapati": ("#b45309", "#fffbeb"),
        "Paratha": ("#f59e0b", "#fef3c7"),
        "Dal": ("#16a34a", "#dcfce7"),
        "Chawal": ("#14b8a6", "#ccfbf1"),
        "Dal Chawal": ("#0ea5e9", "#e0f2fe"),
        "Buttermilk": ("#38bdf8", "#e0f2fe"),
    }
    return palettes.get(name, ("#ff7b54", "#fff4e8"))


# Open the configured backend while keeping the query API shared by both drivers.
def get_connection():
    if os.environ.get("DB_ENGINE", "sqlite").lower() == "mysql":
        import pymysql
        from pymysql.cursors import DictCursor

        return MySQLConnection(
            pymysql.connect(
                host=os.environ.get("MYSQL_HOST", "localhost"),
                port=int(os.environ.get("MYSQL_PORT", "3306")),
                user=os.environ.get("MYSQL_USER", "root"),
                password=os.environ.get("MYSQL_PASSWORD", ""),
                database=os.environ.get("MYSQL_DATABASE", "restaurant_management"),
                charset="utf8mb4",
                cursorclass=DictCursor,
                autocommit=False,
            )
        )

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


# Create tables, migrate older schemas, and seed missing default menu rows.
def init_db():
    # Create the required tables if they do not already exist.
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            image_url TEXT DEFAULT ''
        )
        """
    )

    columns = [row[1] for row in conn.execute("PRAGMA table_info(menu_items)").fetchall()]
    if "image_url" not in columns:
        conn.execute("ALTER TABLE menu_items ADD COLUMN image_url TEXT DEFAULT ''")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            address TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            total REAL NOT NULL,
            customer_id INTEGER,
            customer_name TEXT DEFAULT '',
            customer_phone TEXT DEFAULT '',
            customer_email TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
        """
    )

    order_columns = [row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()]
    for column_name, column_type in {
        "customer_id": "INTEGER",
        "customer_name": "TEXT DEFAULT ''",
        "customer_phone": "TEXT DEFAULT ''",
        "customer_email": "TEXT DEFAULT ''",
    }.items():
        if column_name not in order_columns:
            conn.execute(f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_name TEXT NOT NULL,
            reservation_date TEXT NOT NULL,
            reservation_time TEXT NOT NULL,
            guests INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL DEFAULT 'Staff User',
            role TEXT NOT NULL DEFAULT 'staff'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            customer_id INTEGER,
            payment_method TEXT NOT NULL DEFAULT 'Cash',
            amount REAL NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
        """
    )

    # Seed the database with a menu of common restaurant items and matching image URLs.
    photo_urls = {
        "Burger": "data:image/jpeg;base64,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",
        "Fries": "https://images.unsplash.com/photo-1576107232684-1279f390859f?auto=format&fit=crop&w=900&q=80",
        "Tea": "https://images.unsplash.com/photo-1515823064-d6e0c04616a7?auto=format&fit=crop&w=900&q=80",
        "Pasta": "https://images.unsplash.com/photo-1555949258-eb67b1ef0ceb?auto=format&fit=crop&w=900&q=80",
        "Salad": "https://images.unsplash.com/photo-1546793665-c74683f339c1?auto=format&fit=crop&w=900&q=80",
        "Cake": "https://images.unsplash.com/photo-1551024601-bec78aea704b?auto=format&fit=crop&w=900&q=80",
        "Roti": "https://images.unsplash.com/photo-1604908553252-8d9bb23d4f58?auto=format&fit=crop&w=900&q=80",
        "Chapati": "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=900&q=80",
        "Paratha": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=900&q=80",
        "Dal": "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=900&q=80",
        "Chawal": "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=900&q=80",
        "Dal Chawal": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=900&q=80",
        "Buttermilk": "https://images.unsplash.com/photo-1572449043416-55f4685c9bb7?auto=format&fit=crop&w=900&q=80",
        "Mango Shake": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?auto=format&fit=crop&w=900&q=80",
        "Lassi": "https://images.unsplash.com/photo-1572449043416-55f4685c9bb7?auto=format&fit=crop&w=900&q=80",
        "Nachos": "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=900&q=80",
    }

    default_menu = [
        ("Burger", "Main Course", 199.0, 10, real_photo_data_uri(photo_urls["Burger"], label="Burger", accent="#ff7b54", background="#fff7ed")),
        ("Fries", "Sides", 99.0, 20, real_photo_data_uri(photo_urls["Fries"], label="Fries", accent="#f59e0b", background="#fef3c7")),
        ("Tea", "Beverages", 59.0, 15, real_photo_data_uri(photo_urls["Tea"], label="Tea", accent="#7c3aed", background="#f5f3ff")),
        ("Pasta", "Main Course", 249.0, 8, real_photo_data_uri(photo_urls["Pasta"], label="Pasta", accent="#f97316", background="#ffedd5")),
        ("Salad", "Appetizer", 149.0, 14, real_photo_data_uri(photo_urls["Salad"], label="Salad", accent="#10b981", background="#ecfdf5")),
        ("Cake", "Dessert", 129.0, 9, real_photo_data_uri(photo_urls["Cake"], label="Cake", accent="#ec4899", background="#fdf2f8")),
        ("Chapati", "Main Course", 65.0, 24, real_photo_data_uri(photo_urls["Chapati"], label="Chapati", accent=dish_palette("Chapati")[0], background=dish_palette("Chapati")[1])),
        ("Paratha", "Main Course", 79.0, 22, real_photo_data_uri(photo_urls["Paratha"], label="Paratha", accent=dish_palette("Paratha")[0], background=dish_palette("Paratha")[1])),
        ("Dal", "Main Course", 129.0, 18, real_photo_data_uri(photo_urls["Dal"], label="Dal", accent=dish_palette("Dal")[0], background=dish_palette("Dal")[1])),
        ("Chawal", "Main Course", 119.0, 20, real_photo_data_uri(photo_urls["Chawal"], label="Chawal", accent=dish_palette("Chawal")[0], background=dish_palette("Chawal")[1])),
        ("Dal Chawal", "Main Course", 179.0, 16, real_photo_data_uri(photo_urls["Dal Chawal"], label="Dal Chawal", accent=dish_palette("Dal Chawal")[0], background=dish_palette("Dal Chawal")[1])),
        ("Buttermilk", "Beverages", 69.0, 20, real_photo_data_uri(photo_urls["Buttermilk"], label="Buttermilk", accent=dish_palette("Buttermilk")[0], background=dish_palette("Buttermilk")[1])),
        ("Mango Shake", "Beverages", 109.0, 18, real_photo_data_uri(photo_urls["Mango Shake"], label="Mango Shake", accent="#f59e0b", background="#fef3c7")),
        ("Lassi", "Beverages", 89.0, 17, real_photo_data_uri(photo_urls["Lassi"], label="Lassi", accent="#a855f7", background="#f3e8ff")),
        ("Nachos", "Appetizer", 169.0, 11, real_photo_data_uri(photo_urls["Nachos"], label="Nachos", accent="#fb7185", background="#fff1f2")),
    ]

    valid_names = tuple(name.lower() for name, _, _, _, _ in default_menu)
    if valid_names:
        placeholders = ", ".join("?" for _ in valid_names)
        conn.execute(
            f"DELETE FROM menu_items WHERE LOWER(name) NOT IN ({placeholders})",
            valid_names,
        )

    for name, category, price, stock, image_url in default_menu:
        existing_item = conn.execute(
            "SELECT id FROM menu_items WHERE LOWER(name) = LOWER(?)",
            (name,),
        ).fetchone()

        if existing_item is None:
            conn.execute(
                "INSERT INTO menu_items (name, category, price, stock, image_url) VALUES (?, ?, ?, ?, ?)",
                (name, category, price, stock, image_url),
            )
        else:
            conn.execute(
                """
                UPDATE menu_items
                SET category = ?, price = ?, stock = ?
                WHERE id = ?
                """,
                (category, price, stock, existing_item["id"]),
            )

    admin_count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE LOWER(username) = LOWER(?)",
        ("admin",),
    ).fetchone()[0]
    if admin_count == 0:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "System Administrator", "admin"),
        )

    conn.commit()
    conn.close()


# Menu persistence, including single-item and bulk photo updates.
def get_menu_items():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, category, price, stock, image_url FROM menu_items ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_menu_item_db(name, category, price, stock, image_url=""):
    conn = get_connection()
    existing = conn.execute(
        "SELECT 1 FROM menu_items WHERE LOWER(name) = LOWER(?)",
        (name,),
    ).fetchone()
    if existing:
        conn.close()
        raise ValueError(f"Menu item '{name}' already exists.")

    cursor = conn.execute(
        "INSERT INTO menu_items (name, category, price, stock, image_url) VALUES (?, ?, ?, ?, ?)",
        (name, category, price, stock, image_url or ""),
    )
    conn.commit()
    item_id = cursor.lastrowid
    item = conn.execute(
        "SELECT id, name, category, price, stock, image_url FROM menu_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    conn.close()
    return dict(item)


def update_menu_item_db(item_id, name, category, price, stock, image_url=""):
    if item_id is None:
        raise ValueError("Menu item id is required.")

    cleaned_name = (name or "").strip()
    if not cleaned_name:
        raise ValueError("Item name is required.")
    try:
        numeric_price = float(price)
        numeric_stock = int(stock)
    except (TypeError, ValueError):
        raise ValueError("Price and stock must be valid numbers.") from None

    if numeric_price < 0:
        raise ValueError("Price cannot be negative.")
    if numeric_stock < 0:
        raise ValueError("Stock cannot be negative.")

    conn = get_connection()
    existing = conn.execute(
        "SELECT id, name FROM menu_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    if existing is None:
        conn.close()
        raise ValueError("Menu item not found.")

    duplicate = conn.execute(
        "SELECT id FROM menu_items WHERE LOWER(name) = LOWER(?) AND id != ?",
        (cleaned_name, item_id),
    ).fetchone()
    if duplicate is not None:
        conn.close()
        raise ValueError(f"Menu item '{cleaned_name}' already exists.")

    conn.execute(
        "UPDATE menu_items SET name = ?, category = ?, price = ?, stock = ?, image_url = ? WHERE id = ?",
        (cleaned_name, (category or "General").strip() or "General", numeric_price, numeric_stock, image_url or "", item_id),
    )
    conn.commit()
    item = conn.execute(
        "SELECT id, name, category, price, stock, image_url FROM menu_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    conn.close()
    return dict(item)


def bulk_update_menu_items(items):
    if not isinstance(items, list) or not items:
        raise ValueError("At least one menu item is required.")

    updated_items = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each menu item must be an object.")
        if item.get("id") is None:
            raise ValueError("Each menu item needs an id.")
        updated_items.append(
            update_menu_item_db(
                item["id"], item.get("name", ""), item.get("category", "General"),
                item.get("price", 0), item.get("stock", 0), item.get("image_url", ""),
            )
        )
    return updated_items


def bulk_update_all_menu_photos(image_url):
    image_value = (image_url or "").strip()
    if not image_value:
        raise ValueError("Image URL is required.")

    conn = get_connection()
    conn.execute("UPDATE menu_items SET image_url = ?", (image_value,))
    conn.commit()
    rows = conn.execute(
        "SELECT id, name, category, price, stock, image_url FROM menu_items ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# Customer and payment records are shared by orders and customer history.
def create_customer_db(name, phone="", email="", address=""):
    name = (name or "").strip()
    phone = (phone or "").strip()
    email = (email or "").strip()
    address = (address or "").strip()
    if not name:
        raise ValueError("Customer name is required.")

    conn = get_connection()
    existing = conn.execute(
        """
        SELECT id, name, phone, email, address
        FROM customers
        WHERE LOWER(name) = LOWER(?) OR LOWER(phone) = LOWER(?) OR LOWER(email) = LOWER(?)
        """,
        (name, phone, email),
    ).fetchone()
    if existing is not None:
        if phone or email or address:
            conn.execute(
                "UPDATE customers SET phone = ?, email = ?, address = ? WHERE id = ?",
                (phone or existing["phone"], email or existing["email"], address or existing["address"], existing["id"]),
            )
            conn.commit()
            existing = conn.execute(
                "SELECT id, name, phone, email, address FROM customers WHERE id = ?",
                (existing["id"],),
            ).fetchone()
        conn.close()
        return dict(existing)

    cursor = conn.execute(
        "INSERT INTO customers (name, phone, email, address) VALUES (?, ?, ?, ?)",
        (name, phone, email, address),
    )
    conn.commit()
    customer = conn.execute(
        "SELECT id, name, phone, email, address FROM customers WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    conn.close()
    return dict(customer)


def get_customers():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            id,
            name,
            name AS customer_name,
            phone,
            phone AS customer_phone,
            email,
            email AS customer_email,
            address,
            created_at
        FROM customers
        ORDER BY id DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_payment_db(order_id, customer_id=None, payment_method="Cash", amount=0.0, payment_status="pending"):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO payments (order_id, customer_id, payment_method, amount, payment_status) VALUES (?, ?, ?, ?, ?)",
        (order_id, customer_id, payment_method or "Cash", float(amount), payment_status or "pending"),
    )
    conn.commit()
    payment = conn.execute(
        """
        SELECT p.id, p.order_id, p.customer_id, c.name AS customer_name, p.payment_method, p.amount, p.payment_status, p.created_at
        FROM payments p
        LEFT JOIN customers c ON c.id = p.customer_id
        WHERE p.id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    conn.close()
    return dict(payment)


def get_payments():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT p.id, p.order_id, c.name AS customer_name, c.phone AS customer_phone, c.email AS customer_email,
               p.payment_method, p.amount, p.payment_status, p.created_at
        FROM payments p
        LEFT JOIN customers c ON c.id = p.customer_id
        ORDER BY p.id DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# Validate order lines, update stock, then save the order and its payment.
def create_order_db(
    items,
    table_name="Table 1",
    customer_name=None,
    customer_phone="",
    customer_email="",
    customer_address="",
    payment_method="Cash",
    payment_status="pending",
):
    if not items:
        raise ValueError("No items were provided for the order.")

    conn = get_connection()
    total = 0.0

    for item in items:
        if not isinstance(item, dict):
            conn.close()
            raise ValueError("Each order item must be an object with a name and quantity.")

        name = (item.get("name") or "").strip()
        quantity_raw = item.get("quantity")
        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError):
            conn.close()
            raise ValueError("Each order item needs a valid numeric quantity.")

        if not name or quantity <= 0:
            conn.close()
            raise ValueError("Each order item needs a valid name and quantity.")

        record = conn.execute(
            "SELECT id, name, price, stock FROM menu_items WHERE LOWER(name) = LOWER(?)",
            (name,),
        ).fetchone()
        if record is None:
            conn.close()
            raise ValueError(f"No menu item found for '{name}'.")
        if quantity > record["stock"]:
            conn.close()
            raise ValueError(f"Not enough stock for '{record['name']}'.")

        item_total = record["price"] * quantity
        total += item_total

    customer = None
    customer_name_value = (customer_name or "Walk-in Customer").strip() or "Walk-in Customer"
    if customer_name_value or customer_phone or customer_email:
        customer_row = conn.execute(
            """
            SELECT id, name, phone, email, address
            FROM customers
            WHERE LOWER(name) = LOWER(?) OR LOWER(phone) = LOWER(?) OR LOWER(email) = LOWER(?)
            """,
            (customer_name_value, (customer_phone or ""), (customer_email or "")),
        ).fetchone()

        if customer_row is not None:
            customer = dict(customer_row)
            if customer_phone or customer_email or customer_address:
                conn.execute(
                    """
                    UPDATE customers
                    SET phone = ?, email = ?, address = ?
                    WHERE id = ?
                    """,
                    (
                        customer_phone or customer["phone"],
                        customer_email or customer["email"],
                        customer_address or customer["address"],
                        customer["id"],
                    ),
                )
                customer["phone"] = customer_phone or customer["phone"]
                customer["email"] = customer_email or customer["email"]
                customer["address"] = customer_address or customer["address"]
        else:
            cursor = conn.execute(
                "INSERT INTO customers (name, phone, email, address) VALUES (?, ?, ?, ?)",
                (customer_name_value, customer_phone or "", customer_email or "", customer_address or ""),
            )
            customer = {
                "id": cursor.lastrowid,
                "name": customer_name_value,
                "phone": customer_phone or "",
                "email": customer_email or "",
                "address": customer_address or "",
            }

    order_cursor = conn.execute(
        """
        INSERT INTO orders (table_name, total, customer_id, customer_name, customer_phone, customer_email)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            table_name,
            total,
            customer["id"] if customer else None,
            customer["name"] if customer else customer_name_value,
            customer["phone"] if customer else customer_phone or "",
            customer["email"] if customer else customer_email or "",
        ),
    )
    order_id = order_cursor.lastrowid

    for item in items:
        name = (item.get("name") or "").strip()
        quantity = int(item.get("quantity"))
        menu_item = conn.execute(
            "SELECT price FROM menu_items WHERE LOWER(name) = LOWER(?)",
            (name,),
        ).fetchone()
        conn.execute(
            "INSERT INTO order_items (order_id, name, quantity, unit_price) VALUES (?, ?, ?, ?)",
            (order_id, name, quantity, menu_item["price"]),
        )
        conn.execute(
            "UPDATE menu_items SET stock = stock - ? WHERE LOWER(name) = LOWER(?)",
            (quantity, name),
        )

    conn.execute(
        "INSERT INTO payments (order_id, customer_id, payment_method, amount, payment_status) VALUES (?, ?, ?, ?, ?)",
        (
            order_id,
            customer["id"] if customer else None,
            payment_method or "Cash",
            total,
            payment_status or "pending",
        ),
    )

    conn.commit()
    conn.close()
    return total


# Dashboard summary values and reservation persistence.
def get_summary():
    conn = get_connection()
    total_sales = conn.execute("SELECT COALESCE(SUM(total), 0) FROM orders").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    alerts = conn.execute("SELECT COUNT(*) FROM menu_items WHERE stock < 10").fetchone()[0]
    conn.close()
    return {
        "sales": float(total_sales),
        "total_orders": int(total_orders),
        "alerts": int(alerts),
    }


def get_reservations():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, guest_name, reservation_date, reservation_time, guests FROM reservations ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_reservation_db(guest_name, reservation_date, reservation_time, guests):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO reservations (guest_name, reservation_date, reservation_time, guests) VALUES (?, ?, ?, ?)",
        (guest_name, reservation_date, reservation_time, guests),
    )
    conn.commit()
    reservation_id = cursor.lastrowid
    reservation = conn.execute(
        "SELECT id, guest_name, reservation_date, reservation_time, guests FROM reservations WHERE id = ?",
        (reservation_id,),
    ).fetchone()
    conn.close()
    return dict(reservation)


# Store password hashes rather than plaintext passwords.
def create_user_db(username, password, full_name="Staff User", role="staff"):
    username = (username or "").strip()
    full_name = (full_name or "Staff User").strip() or "Staff User"
    role = (role or "staff").strip() or "staff"

    if not username:
        raise ValueError("Username is required.")
    if len(password or "") < 6:
        raise ValueError("Password must be at least 6 characters long.")

    conn = get_connection()
    existing = conn.execute(
        "SELECT 1 FROM users WHERE LOWER(username) = LOWER(?)",
        (username,),
    ).fetchone()
    if existing:
        conn.close()
        raise ValueError(f"Username '{username}' already exists.")

    cursor = conn.execute(
        "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
        (username, generate_password_hash(password), full_name, role),
    )
    conn.commit()
    user_id = cursor.lastrowid
    user = conn.execute(
        "SELECT id, username, full_name, role FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(user)


def verify_user_db(username, password):
    username = (username or "").strip()
    if not username or not password:
        return None

    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, password_hash, full_name, role FROM users WHERE LOWER(username) = LOWER(?)",
        (username,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    if not check_password_hash(row["password_hash"], password):
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"],
        "role": row["role"],
    }
