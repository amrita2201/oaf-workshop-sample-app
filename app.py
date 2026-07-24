from flask import Flask, render_template, request, redirect, send_from_directory
import os
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def init_db():
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            course TEXT,
            semester TEXT,
            filename TEXT,
            uploaded_at TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        title = request.form["title"]
        course = request.form["course"]
        semester = request.form["semester"]
        file = request.files["file"]

        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            conn = sqlite3.connect("notes.db")
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO notes
                (title, course, semester, filename, uploaded_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    title,
                    course,
                    semester,
                    filename,
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                )
            )
            conn.commit()
            conn.close()

        return redirect("/notes")

    return render_template("upload.html")


@app.route("/notes")
def notes():
    search = request.args.get("search", "")

    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    if search:
        cursor.execute(
            """
            SELECT * FROM notes
            WHERE title LIKE ? OR course LIKE ?
            """,
            (f"%{search}%", f"%{search}%")
        )
    else:
        cursor.execute("SELECT * FROM notes")

    notes_data = cursor.fetchall()
    conn.close()

    return render_template(
        "notes.html",
        notes=notes_data,
        search=search
    )


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        as_attachment=True
    )


@app.route("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
