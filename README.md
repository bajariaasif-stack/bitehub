# BiteHub — Restaurant Management System

BiteHub is a Flask-based restaurant management application with a browser interface for menu and inventory management, orders, customers, payments, reservations, and sales summaries.

## Features

- Login and session-based UI access
- Menu items, prices, stock, and dish photos
- Order creation with stock updates
- Customer records and payment history
- Table reservations and sales summary
- SQLite by default, with optional MySQL configuration

## Requirements

- Python 3.10 or newer
- Dependencies listed in `requirements.txt`

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser.

The application initializes its database on startup. By default, SQLite data is stored in `restaurant.db` next to `database.py`.

## Configuration

Set `SECRET_KEY` to a long, random value before deploying. The current development fallback is not suitable for production.

For MySQL, set `DB_ENGINE=mysql` and configure `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE`. Keep credentials in environment variables; do not commit secrets.

## Tests

```bash
python -m pytest -q
```

## Deployment notes

- Use a production WSGI server (for example, Gunicorn) instead of Flask's development server.
- Configure a strong `SECRET_KEY` and HTTPS.
- Review authentication and authorization for every API endpoint before exposing the app publicly.
- Keep the live database and customer/order data out of version control.
