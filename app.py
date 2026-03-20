import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import black, lightgrey
from reportlab.lib.styles import getSampleStyleSheet
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, send_file, redirect, session
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import sqlite3
import joblib
import io

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXTee
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        heart_risk REAL,
        diabetes_risk REAL,
        heart_level TEXT,
        diabetes_level TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

init_db()

def create_admin():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if not cursor.fetchone():
        hashed = generate_password_hash("1234")
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                       ("admin", hashed))
        conn.commit()

    conn.close()
create_admin()

app = Flask(__name__)
app.secret_key = "secret_key"

heart_model = joblib.load("models/heart_model.pkl")
diabetes_model = joblib.load("models/diabetes_model.pkl")
dataset = pd.read_csv("dataset/biomedical heart and diabetes dataset.csv")
X = dataset.drop(["heart_disease","diabetes_risk","patient_id"], axis=1)
feature_names = X.columns

def get_risk_level(prob):
    if prob < 30:
        return "Low", "#1abc9c"
    elif prob < 70:
        return "Medium", "#f39c12"
    else:
        return "High", "#e32828"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    user_input = request.form["patient_data"]
    values = [float(x) for x in user_input.split(",")]
    patient_id = int(values[0])
    features = values[1:]

    input_data = pd.DataFrame([features], columns=feature_names)
    heart_prob = heart_model.predict_proba(input_data)[0][1] * 100
    diabetes_prob = diabetes_model.predict_proba(input_data)[0][1] * 100
    heart_prob = round(heart_prob,2)
    diabetes_prob = round(diabetes_prob,2)
    heart_level, heart_color = get_risk_level(heart_prob)
    diabetes_level, diabetes_color = get_risk_level(diabetes_prob)
   
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO predictions (patient_id, heart_risk, diabetes_risk, heart_level, diabetes_level)
    VALUES (?, ?, ?, ?, ?)
    """, (patient_id, heart_prob, diabetes_prob, heart_level, diabetes_level))
    conn.commit()
    conn.close()

    heart_level, heart_color = get_risk_level(heart_prob)
    diabetes_level, diabetes_color = get_risk_level(diabetes_prob)

    return render_template(
        "result.html",
        patient_id=patient_id,
        heart=heart_prob,
        diabetes=diabetes_prob,
        heart_level=heart_level,
        diabetes_level=diabetes_level,
        heart_color=heart_color,
        diabetes_color=diabetes_color
    )

@app.route("/history")
def history():
    if not session.get("admin"):
        return redirect("/")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM predictions ORDER BY timestamp DESC")
    data = cursor.fetchall()
    conn.close()

    return render_template("history.html", data=data)

@app.route("/download_report")
def download_report():

    heart = request.args.get("heart")
    diabetes = request.args.get("diabetes")
    heart_level = request.args.get("heart_level")
    diabetes_level = request.args.get("diabetes_level")
    patient_id = request.args.get("patient_id")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>AI Health Risk Prediction Report</b>", styles['Title']))
    elements.append(Spacer(1,20))

    elements.append(Paragraph(f"<b>Patient ID:</b> {patient_id}", styles['Normal']))
    elements.append(Spacer(1,20))

    data = [
        ["Disease", "Risk Percentage", "Risk Level"],
        ["Heart Disease", f"{heart} %", heart_level],
        ["Diabetes", f"{diabetes} %", diabetes_level]
    ]

    table = Table(data, colWidths=[180,150,120])
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),lightgrey),
        ("TEXTCOLOR",(0,0),(-1,0),black),
        ("GRID",(0,0),(-1,-1),1,black),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("ALIGN",(1,1),(-1,-1),"CENTER")
    ]))

    elements.append(table)
    elements.append(Spacer(1,30))

    elements.append(Paragraph("<b>Recommended Diet Plan</b>", styles['Heading2']))
    elements.append(Spacer(1,10))

    diet_list = [
        "Prefer low-GI foods like oats and whole grains",
        "Include high fiber cereals and legumes",
        "Eat leafy vegetables and fruits daily",
        "Avoid fried and processed food",
        "Reduce sugar and refined carbohydrates",
        "Drink 2.5 – 3 liters of water daily"
    ]

    for item in diet_list:
        elements.append(Paragraph(f"• {item}", styles['Normal']))

    elements.append(Spacer(1,20))
    elements.append(Paragraph("<b>Recommended Workout Plan</b>", styles['Heading2']))
    elements.append(Spacer(1,10))

    workout_list = [
        "30–40 minutes brisk walking or cycling",
        "3–4 days cardio exercise per week",
        "Strength training 2–3 times weekly",
        "Daily stretching or yoga (10–15 min)",
        "Maintain healthy body weight",
        "Practice meditation for stress control"
    ]

    for item in workout_list:
        elements.append(Paragraph(f"• {item}", styles['Normal']))

    elements.append(Spacer(1,30))

    elements.append(Paragraph(
        "<i>This report is generated by the AI Health Prediction System. "
        "Consult a healthcare professional for medical advice.</i>",
        styles['Italic']
    ))

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Prediction report.pdf",
        mimetype="application/pdf"
    )

@app.route("/admin_login", methods=["POST"])
def admin_login():
    user = request.form["username"]
    password = request.form["password"]
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username=?", (user,))
    data = cursor.fetchone()
    conn.close()
    if data and check_password_hash(data[0], password):
        session["admin"] = True
        return redirect("/history")
    else:
        return "Invalid login"

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

@app.route("/delete/<int:id>", methods=["DELETE"])
def delete(id):
    if not session.get("admin"):
        return {"success": False}, 401

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM predictions WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return {"success": True}

if __name__ == "__main__":
    app.run(debug=True)