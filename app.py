import socket
import sqlite3

from flask import (
    Flask,
    flash,
    redirect,
    render_template_string,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = "community-health-workshop-key"

DB_FILE = "healthcare_supplies.db"


# --- DATABASE SETUP ---
def init_sqlite_db():
    """Create the healthcare-supply database and add sample items."""

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS supplies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            available_quantity INTEGER NOT NULL
        )
        """
    )

    cursor.execute("SELECT COUNT(*) FROM supplies")

    if cursor.fetchone()[0] == 0:
        sample_supplies = [
            ("First Aid Kit", "Emergency Care", 10),
            ("Digital Thermometer", "Diagnostic Equipment", 8),
            ("Face Mask Pack", "Protective Equipment", 20),
            ("Hand Sanitizer", "Hygiene", 15),
            ("Blood Pressure Monitor", "Diagnostic Equipment", 5),
        ]

        cursor.executemany(
            """
            INSERT INTO supplies
            (name, category, available_quantity)
            VALUES (?, ?, ?)
            """,
            sample_supplies,
        )

        conn.commit()

    conn.close()


init_sqlite_db()


# --- HELPER FUNCTIONS ---
def get_hostname():
    """Return the EC2 hostname to demonstrate ALB load balancing."""

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
    <title>Community Healthcare Supply Tracker</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 30px;
            background-color: #f4f8f7;
        }

        .container {
            max-width: 950px;
            margin: auto;
        }

        .header {
            background-color: #00695c;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .server-banner {
            background-color: #e0f2f1;
            border: 1px solid #00897b;
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 5px;
        }

        .supply-card {
            border: 1px solid #cccccc;
            padding: 16px;
            margin-bottom: 12px;
            background-color: white;
            width: 360px;
            border-radius: 7px;
        }

        .category {
            color: #555555;
        }

        .low-stock {
            color: #c62828;
            font-weight: bold;
        }

        button {
            background-color: #00796b;
            color: white;
            border: none;
            padding: 9px 14px;
            border-radius: 4px;
            cursor: pointer;
        }

        button:hover {
            background-color: #004d40;
        }

        .alert {
            padding: 10px;
            margin-bottom: 15px;
            border-radius: 4px;
        }

        .alert-success {
            background-color: #d4edda;
            color: #155724;
        }

        .alert-danger {
            background-color: #f8d7da;
            color: #721c24;
        }

        a {
            color: #00695c;
            font-weight: bold;
        }
    </style>
</head>

<body>
<div class="container">

    <div class="header">
        <h1>Community Healthcare Supply Tracker</h1>
        <p>View and request available healthcare resources.</p>
    </div>

    <div class="server-banner">
        <strong>Request served by EC2 hostname:</strong>
        {{ hostname }}
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">
                    {{ message }}
                </div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <p>
        <a href="{{ url_for('index') }}">Available Supplies</a>
        |
        <a href="{{ url_for('view_request') }}">
            My Request ({{ total_requested_items }})
        </a>
    </p>

    <hr>

    {% block content %}{% endblock %}

</div>
</body>
</html>
"""


SUPPLIES_TEMPLATE = HTML_LAYOUT.replace(
    "{% block content %}{% endblock %}",
    """
    <h2>Available Healthcare Supplies</h2>

    {% for item in items %}
        <div class="supply-card">
            <h3>{{ item['name'] }}</h3>

            <p class="category">
                Category: {{ item['category'] }}
            </p>

            <p>
                Available quantity:
                {{ item['available_quantity'] }}
            </p>

            {% if item['available_quantity'] <= 5 %}
                <p class="low-stock">
                    Limited availability
                </p>
            {% endif %}

            <form
                action="{{ url_for('add_to_request', item_id=item['id']) }}"
                method="post"
            >
                <button type="submit">
                    Add to Supply Request
                </button>
            </form>
        </div>
    {% endfor %}
    """,
)


REQUEST_TEMPLATE = HTML_LAYOUT.replace(
    "{% block content %}{% endblock %}",
    """
    <h2>My Healthcare Supply Request</h2>

    <p>
        Supplies are checked against the available database quantity
        when the request is submitted.
    </p>

    {% if requested_items %}
        <ul>
        {% for item_id, details in requested_items.items() %}
            <li>
                <strong>{{ details['name'] }}</strong>
                — Quantity requested: {{ details['quantity'] }}
            </li>
        {% endfor %}
        </ul>

        <form
            action="{{ url_for('submit_request') }}"
            method="post"
            style="margin-top: 15px;"
        >
            <button type="submit">
                Submit Supply Request
            </button>
        </form>
    {% else %}
        <p>No healthcare supplies have been requested.</p>
    {% endif %}
    """,
)


# --- ROUTES ---
@app.route("/")
def index():
    db = get_db()

    items = db.execute(
        """
        SELECT *
        FROM supplies
        ORDER BY category, name
        """
    ).fetchall()

    db.close()

    requested_items = session.get("requested_items", {})

    total_requested_items = sum(
        item["quantity"]
        for item in requested_items.values()
    )

    return render_template_string(
        SUPPLIES_TEMPLATE,
        items=items,
        hostname=get_hostname(),
        total_requested_items=total_requested_items,
    )


@app.route("/request/add/<int:item_id>", methods=["POST"])
def add_to_request(item_id):
    """Add a healthcare supply to the user's session request."""

    db = get_db()

    item = db.execute(
        """
        SELECT *
        FROM supplies
        WHERE id = ?
        """,
        (item_id,),
    ).fetchone()

    db.close()

    if not item:
        flash("Healthcare supply was not found.", "danger")
        return redirect(url_for("index"))

    if item["available_quantity"] <= 0:
        flash(
            f"{item['name']} is currently unavailable.",
            "danger",
        )
        return redirect(url_for("index"))

    requested_items = session.get("requested_items", {})
    item_key = str(item_id)

    if item_key in requested_items:
        requested_items[item_key]["quantity"] += 1
    else:
        requested_items[item_key] = {
            "name": item["name"],
            "quantity": 1,
        }

    session["requested_items"] = requested_items

    flash(
        f"{item['name']} was added to your request.",
        "success",
    )

    return redirect(url_for("index"))


@app.route("/request")
def view_request():
    requested_items = session.get("requested_items", {})

    total_requested_items = sum(
        item["quantity"]
        for item in requested_items.values()
    )

    return render_template_string(
        REQUEST_TEMPLATE,
        requested_items=requested_items,
        hostname=get_hostname(),
        total_requested_items=total_requested_items,
    )


@app.route("/request/submit", methods=["POST"])
def submit_request():
    """Validate quantities and update healthcare-supply availability."""

    requested_items = session.get("requested_items", {})

    if not requested_items:
        flash("Your healthcare supply request is empty.", "danger")
        return redirect(url_for("index"))

    db = get_db()

    try:
        cursor = db.cursor()

        # Check availability for every requested item.
        for item_id_string, details in requested_items.items():
            item_id = int(item_id_string)
            requested_quantity = details["quantity"]

            row = cursor.execute(
                """
                SELECT name, available_quantity
                FROM supplies
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()

            if not row:
                raise ValueError(
                    f"{details['name']} is no longer available."
                )

            if row["available_quantity"] < requested_quantity:
                raise ValueError(
                    f"Insufficient quantity for {row['name']}. "
                    f"Requested: {requested_quantity}, "
                    f"Available: {row['available_quantity']}."
                )

        # Update quantity only when every item is available.
        for item_id_string, details in requested_items.items():
            item_id = int(item_id_string)
            requested_quantity = details["quantity"]

            cursor.execute(
                """
                UPDATE supplies
                SET available_quantity = available_quantity - ?
                WHERE id = ?
                """,
                (requested_quantity, item_id),
            )

        db.commit()

        session["requested_items"] = {}

        flash(
            "Healthcare supply request submitted successfully.",
            "success",
        )

    except Exception as error:
        db.rollback()

        flash(
            f"Request could not be completed: {error}",
            "danger",
        )

    finally:
        db.close()

    return redirect(url_for("index"))


@app.route("/health")
def health():
    """Endpoint used by the Application Load Balancer health check."""

    return {
        "status": "healthy",
        "application": "community-healthcare-supply-tracker",
        "hostname": get_hostname(),
    }


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=80,
    )
