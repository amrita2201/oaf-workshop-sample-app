import os
import socket
import sqlite3
from flask import Flask, render_template_string, request, session, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "super-secret-workshop-key"  # Required for sessions
DB_FILE = "ecommerce.db"

# --- DATABASE SETUP ---
def init_sqlite_db():
    """Initializes the database with sample products if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    ''')
    # Seed initial items if empty
    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        sample_items = [
            ("Wireless Mouse", 25.00, 10),
            ("Mechanical Keyboard", 85.00, 5),
            ("HD Monitor", 150.00, 3),
            ("USB-C Hub", 30.00, 12)
        ]
        cursor.executemany("INSERT INTO inventory (name, price, stock) VALUES (?, ?, ?)", sample_items)
        conn.commit()
    conn.close()

init_sqlite_db()

# --- HELPER FUNCTIONS ---
def get_hostname():
    """Returns hostname to show ALB load balancing in action."""
    return socket.gethostname()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- HTML TEMPLATES ---
HTML_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <title>E-Commerce Workshop</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 30px; background-color: #f9f9f9; }
        .server-banner { background: #e0f7fa; border: 1px solid #00838f; padding: 10px; margin-bottom: 20px; border-radius: 4px; }
        .item-card { border: 1px solid #ccc; padding: 15px; margin-bottom: 10px; background: #fff; width: 300px; border-radius: 4px; }
        button { background: #007bff; color: white; border: none; padding: 8px 12px; border-radius: 3px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .alert { padding: 10px; margin-bottom: 15px; border-radius: 4px; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-danger { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="server-banner">
        <strong>Served by EC2 Hostname:</strong> {{ hostname }}
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <p><a href="{{ url_for('index') }}">Catalog</a> | <a href="{{ url_for('view_cart') }}">Cart ({{ total_cart_items }})</a></p>
    <hr>
    {% block content %}{% endblock %}
</body>
</html>
"""

CATALOG_TEMPLATE = HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
<h2>Product Catalog</h2>
{% for item in items %}
  <div class="item-card">
    <h3>{{ item['name'] }}</h3>
    <p>Price: ${{ "%.2f"|format(item['price']) }}</p>
    <p>Stock in DB: {{ item['stock'] }}</p>
    <form action="{{ url_for('add_to_cart', item_id=item['id']) }}" method="post">
        <button type="submit">Add to Cart</button>
    </form>
  </div>
{% endfor %}
""")

CART_TEMPLATE = HTML_LAYOUT.replace("{% block content %}{% endblock %}", """
<h2>Your Shopping Cart</h2>
<p><i>Note: Cart updates happen independently in your session. Stock is only checked on checkout.</i></p>

{% if cart %}
    <ul>
    {% for item_id, details in cart.items() %}
        <li><strong>{{ details['name'] }}</strong> — Qty: {{ details['qty'] }}</li>
    {% endfor %}
    </ul>
    
    <form action="{{ url_for('checkout') }}" method="post" style="margin-top: 15px;">
        <button type="submit" style="background-color: #28a745;">Proceed to Checkout</button>
    </form>
{% else %}
    <p>Your cart is empty.</p>
{% endif %}
""")

# --- ROUTES ---
@app.route("/")
def index():
    db = get_db()
    items = db.execute("SELECT * FROM inventory").fetchall()
    db.close()
    
    cart = session.get("cart", {})
    total_cart_items = sum(item["qty"] for item in cart.values())
    
    return render_template_string(CATALOG_TEMPLATE, items=items, hostname=get_hostname(), total_cart_items=total_cart_items)

@app.route("/add/<int:item_id>", methods=["POST"])
def add_to_cart(item_id):
    """Adds item to session cart independently without touching the database stock."""
    db = get_db()
    item = db.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
    db.close()

    if not item:
        flash("Item not found.", "danger")
        return redirect(url_for("index"))

    cart = session.get("cart", {})
    str_id = str(item_id)
    
    if str_id in cart:
        cart[str_id]["qty"] += 1
    else:
        cart[str_id] = {"name": item["name"], "qty": 1}
    
    session["cart"] = cart
    flash(f"Added {item['name']} to cart!", "success")
    return redirect(url_for("index"))

@app.route("/cart")
def view_cart():
    cart = session.get("cart", {})
    total_cart_items = sum(item["qty"] for item in cart.values())
    return render_template_string(CART_TEMPLATE, cart=cart, hostname=get_hostname(), total_cart_items=total_cart_items)

@app.route("/checkout", methods=["POST"])
def checkout():
    """Checks stock and completes purchase atomically upon checkout."""
    cart = session.get("cart", {})
    if not cart:
        flash("Cart is empty.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    try:
        # Begin transaction
        cursor = db.cursor()
        
        # Verify inventory for each item in cart
        for item_id_str, details in cart.items():
            item_id = int(item_id_str)
            qty_requested = details["qty"]
            
            row = cursor.execute("SELECT stock, name FROM inventory WHERE id = ?", (item_id,)).fetchone()
            if not row:
                raise ValueError(f"Item '{details['name']}' no longer exists.")
            
            current_stock = row["stock"]
            if current_stock < qty_requested:
                raise ValueError(f"Not enough stock for '{row['name']}'. Requested: {qty_requested}, Available: {current_stock}")

        # Deduct inventory if all checks pass
        for item_id_str, details in cart.items():
            item_id = int(item_id_str)
            qty_requested = details["qty"]
            cursor.execute("UPDATE inventory SET stock = stock - ? WHERE id = ?", (qty_requested, item_id))
        
        db.commit()
        session["cart"] = {}  # Clear cart
        flash("Checkout successful! Inventory updated.", "success")
        
    except Exception as e:
        db.rollback()
        flash(f"Checkout failed: {str(e)}", "danger")
    finally:
        db.close()

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
