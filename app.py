
from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "telemedicine_secret_key"


# ---------------- DATABASE ----------------

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = get_db_connection()

    # Module 1: Users
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Module 2: Patient symptom reports
    conn.execute("""
        CREATE TABLE IF NOT EXISTS symptom_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            symptoms TEXT NOT NULL,
            duration TEXT NOT NULL,
            severity TEXT NOT NULL,
            triage_result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("login.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        role = request.form["role"]

        # Only allow supported roles
        if role not in ["Patient", "Doctor", "Admin"]:
            return "Invalid role selected.", 400

        if not name or not email or not password:
            return "Please fill in all fields.", 400

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()

        try:
            conn.execute(
                """
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, ?)
                """,
                (name, email, hashed_password, role)
            )
            conn.commit()

        except sqlite3.IntegrityError:
            conn.close()
            return "Email already registered!"

        conn.close()
        return redirect("/")

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"].strip()
    password = request.form["password"]

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user["password"], password):
        session.clear()
        session["user_id"] = user["id"]
        session["name"] = user["name"]
        session["role"] = user["role"]

        if user["role"] == "Patient":
            return redirect("/patient")
        elif user["role"] == "Doctor":
            return redirect("/doctor")
        elif user["role"] == "Admin":
            return redirect("/admin")

    return "Invalid email or password!"


# ---------------- PATIENT DASHBOARD ----------------

@app.route("/patient")
def patient():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "Patient":
        return "Access Denied", 403

    return render_template(
        "patient_dashboard.html",
        name=session["name"]
    )


# ---------------- MODULE 2: SYMPTOM INTAKE ----------------

@app.route("/symptom-intake", methods=["GET", "POST"])
def symptom_intake():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "Patient":
        return "Access Denied", 403

    result = None
    error = None

    if request.method == "POST":
        symptoms = request.form.get("symptoms", "").strip()
        duration = request.form.get("duration", "")
        severity = request.form.get("severity", "")

        valid_durations = [
            "Less than 1 day",
            "1-3 days",
            "More than 3 days"
        ]
        valid_severities = ["Mild", "Moderate", "Severe"]

        if (
            not symptoms
            or duration not in valid_durations
            or severity not in valid_severities
        ):
            error = "Please enter symptoms and select valid options."

        else:
            # Simple predefined rules; not AI or machine learning.
            if severity == "Severe":
                result = (
                    "URGENT: Seek immediate medical assessment. "
                    "If symptoms are severe, sudden, or life-threatening, "
                    "contact local emergency services."
                )
            elif severity == "Moderate":
                result = (
                    "PROMPT REVIEW: Contact a qualified healthcare "
                    "professional for assessment, especially if symptoms "
                    "are worsening."
                )
            elif duration == "More than 3 days":
                result = (
                    "MEDICAL REVIEW: Consider contacting a healthcare "
                    "professional because symptoms have persisted."
                )
            else:
                result = (
                    "GENERAL GUIDANCE: This basic prototype cannot "
                    "determine whether your condition is safe. Monitor "
                    "your symptoms and seek medical advice if they persist "
                    "or worsen."
                )

            conn = get_db_connection()
            conn.execute(
                """
                INSERT INTO symptom_reports
                (patient_id, symptoms, duration, severity, triage_result)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    symptoms,
                    duration,
                    severity,
                    result
                )
            )
            conn.commit()
            conn.close()

    return render_template(
        "symptom_intake.html",
        name=session["name"],
        result=result,
        error=error
    )


# ---------------- PATIENT REPORT HISTORY ----------------

@app.route("/my-reports")
def my_reports():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "Patient":
        return "Access Denied", 403

    conn = get_db_connection()
    reports = conn.execute(
        """
        SELECT symptoms, duration, severity, triage_result, created_at
        FROM symptom_reports
        WHERE patient_id = ?
        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template(
        "my_reports.html",
        name=session["name"],
        reports=reports
    )


# ---------------- DOCTOR DASHBOARD ----------------

@app.route("/doctor")
def doctor():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "Doctor":
        return "Access Denied", 403

    return render_template(
        "doctor_dashboard.html",
        name=session["name"]
    )


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
def admin():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "Admin":
        return "Access Denied", 403

    return render_template(
        "admin_dashboard.html",
        name=session["name"]
    )


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- START ----------------

if __name__ == "__main__":
    create_database()
    app.run(debug=True)
