"""Behavior tests for web routes, database persistence, and order calculations."""

from database import create_customer_db, create_order_db, get_customers, get_payments
from restaurant import RestaurantManagementSystem, MenuItem
from app import app


def test_web_app_serves_login_page():
    client = app.test_client()

    login_response = client.get('/login')

    assert login_response.status_code == 200
    assert b'login' in login_response.data.lower()


def test_user_login_flow():
    client = app.test_client()

    login_response = client.post(
        '/api/login',
        json={'username': 'admin', 'password': 'admin123'},
    )

    assert login_response.status_code == 200
    assert login_response.is_json
    assert login_response.json['user']['username'] == 'admin'

    menu_response = client.get('/api/menu')
    assert menu_response.status_code == 200
    assert menu_response.is_json


def test_menu_and_order_flow():
    system = RestaurantManagementSystem()

    system.add_menu_item("Burger", 15.0, category="Main Course", stock=10)
    system.add_menu_item("Fries", 5.0, category="Sides", stock=20)

    assert len(system.menu) == 2
    assert system.menu[0].name == "Burger"

    order = system.create_order()
    order.add_item("Burger", 2)
    order.add_item("Fries", 1)

    assert order.total == 35.0

    system.process_order(order)

    assert system.sales == 35.0
    assert system.menu[0].stock == 8
    assert system.menu[1].stock == 19


def test_required_indian_meals_are_available():
    from database import get_menu_items

    menu = get_menu_items()
    names = {item["name"] for item in menu}

    assert "Dal" in names
    assert "Chawal" in names
    assert "Roti" not in names
    assert "Paratha" in names


def test_database_initialization_preserves_custom_menu_photos(tmp_path, monkeypatch):
    import database

    monkeypatch.setenv("DB_ENGINE", "sqlite")
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "restaurant.db"))
    monkeypatch.setattr(database, "real_photo_data_uri", lambda *args, **kwargs: "seed-photo")

    database.init_db()
    connection = database.get_connection()
    connection.execute(
        "UPDATE menu_items SET image_url = ? WHERE name = ?",
        ("custom-photo", "Burger"),
    )
    connection.commit()
    connection.close()

    database.init_db()

    burger = next(item for item in database.get_menu_items() if item["name"] == "Burger")
    assert burger["image_url"] == "custom-photo"


def test_order_accepts_numeric_string_quantities():
    total = create_order_db(
        [{"name": "Burger", "quantity": "2"}],
        table_name="Table 9",
        customer_name="Test User",
        customer_phone="9999988888",
        customer_email="test@example.com",
        payment_method="Card",
        payment_status="paid",
    )

    assert total == 398.0


def test_invalid_menu_item_rejected():
    system = RestaurantManagementSystem()

    item = MenuItem("Tea", 3.0, "Beverages", stock=5)
    system.add_menu_item(item)

    assert system.get_menu_item("Tea").price == 3.0
    assert system.get_menu_item("Coffee") is None


def test_invalid_menu_and_order_inputs_are_rejected():
    system = RestaurantManagementSystem()

    try:
        system.add_menu_item("Coffee", None, category="Beverages", stock=5)
        assert False, "Expected ValueError for invalid menu price"
    except ValueError:
        pass

    order = system.create_order()
    try:
        order.add_item("   ", 2)
        assert False, "Expected ValueError for blank item name"
    except ValueError:
        pass


def test_menu_item_can_be_updated_via_api():
    client = authenticated_client()

    create_response = client.post(
        '/api/menu',
        json={
            'name': 'Crispy Tacos',
            'category': 'Appetizer',
            'price': 180,
            'stock': 8,
            'image_url': 'https://example.com/taco.jpg',
        },
    )
    assert create_response.status_code == 201
    item_id = create_response.json['id']

    update_response = client.put(
        '/api/menu',
        json={
            'id': item_id,
            'name': 'Crispy Tacos',
            'category': 'Appetizer',
            'price': 220,
            'stock': 12,
            'image_url': 'https://example.com/taco-new.jpg',
        },
    )

    assert update_response.status_code == 200
    assert update_response.json['price'] == 220.0
    assert update_response.json['stock'] == 12
    assert update_response.json['image_url'] == 'https://example.com/taco-new.jpg'


def test_bulk_menu_updates_and_photo_updates_via_api():
    client = authenticated_client()

    menu_response = client.get('/api/menu')
    assert menu_response.status_code == 200
    items = menu_response.json
    first_item = items[0]
    second_item = items[1]
    original_first = dict(first_item)
    original_second = dict(second_item)

    bulk_response = client.put(
        '/api/menu/bulk',
        json={
            'items': [
                {
                    'id': first_item['id'],
                    'name': first_item['name'],
                    'category': first_item['category'],
                    'price': first_item['price'] + 10,
                    'stock': first_item['stock'] + 2,
                    'image_url': 'https://example.com/first-photo.jpg',
                },
                {
                    'id': second_item['id'],
                    'name': second_item['name'],
                    'category': second_item['category'],
                    'price': second_item['price'] + 5,
                    'stock': second_item['stock'] + 3,
                    'image_url': 'https://example.com/second-photo.jpg',
                },
            ]
        },
    )
    assert bulk_response.status_code == 200
    assert bulk_response.json[0]['image_url'] == 'https://example.com/first-photo.jpg'
    assert bulk_response.json[1]['image_url'] == 'https://example.com/second-photo.jpg'

    apply_photo_response = client.put(
        '/api/menu/bulk',
        json={'image_url': 'https://example.com/shared-photo.jpg', 'apply_to_all': True},
    )
    assert apply_photo_response.status_code == 200
    assert all(item['image_url'] == 'https://example.com/shared-photo.jpg' for item in apply_photo_response.json)

    restore_response = client.put(
        '/api/menu/bulk',
        json={
            'items': [
                {
                    'id': original_first['id'],
                    'name': original_first['name'],
                    'category': original_first['category'],
                    'price': original_first['price'],
                    'stock': original_first['stock'],
                    'image_url': original_first['image_url'],
                },
                {
                    'id': original_second['id'],
                    'name': original_second['name'],
                    'category': original_second['category'],
                    'price': original_second['price'],
                    'stock': original_second['stock'],
                    'image_url': original_second['image_url'],
                },
            ]
        },
    )
    assert restore_response.status_code == 200


def test_customer_and_payment_flow():
    customer = create_customer_db(
        "Alice Johnson",
        phone="1234567890",
        email="alice@example.com",
        address="123 Market Street",
    )

    assert customer["name"] == "Alice Johnson"
    assert customer["phone"] == "1234567890"

    total = create_order_db(
        [{"name": "Burger", "quantity": 2}, {"name": "Fries", "quantity": 1}],
        table_name="Table 5",
        customer_name="Alice Johnson",
        customer_phone="1234567890",
        customer_email="alice@example.com",
        payment_method="Card",
        payment_status="paid",
    )

    assert total == 497.0
    assert any(row["customer_name"] == "Alice Johnson" for row in get_customers())
    assert any(row["payment_method"] == "Card" and row["amount"] == 497.0 for row in get_payments())


def test_api_rejects_unauthenticated_requests():
    client = app.test_client()
    response = client.get('/api/menu')
    assert response.status_code == 401


def test_registration_requires_admin():
    client = app.test_client()
    response = client.post('/api/register', json={
        'username': 'should-not-register', 'password': 'test-password', 'role': 'staff'
    })
    assert response.status_code == 401
