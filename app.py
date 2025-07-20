import os
import re
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from dotenv import load_dotenv
from flask import send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

load_dotenv()
app = Flask(__name__)
app.secret_key = "your_dev_secret_123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session.get('username'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!')
            return redirect(url_for('index'))
        else:
            flash('❌ Invalid email or password. Please try again or register.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    #flash('Logged out.')
    return redirect(url_for('login'))

def extract_followups(text):
    lines = text.splitlines()
    followups = []
    for line in lines:
        if re.match(r"[\-•]?\s*.+\?$", line.strip()):
            followups.append(line.strip('•- ').strip())
    return followups

def strip_followups_from_reply(text):
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        if not re.match(r"[\-•]?\s*.+\?$", line.strip()):
            cleaned.append(line)
    return "\n".join(cleaned).strip()

@app.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({"reply": "❌ Please login first."}), 401

    user_message = request.json['message']
    chat_history = request.json.get('history', [])
    lang_code = request.json.get('target_lang')
    print("target lang", lang_code)

    lang_native_names = {
        "en": "English",
        "hi": "Hindi",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "zh": "Chinese"
    }

    target_lang = lang_native_names.get(lang_code, "English")

    itinerary_match = re.search(r'(\d+)[-\s]?day', user_message.lower())
    is_itinerary = bool(itinerary_match)
    days = int(itinerary_match.group(1)) if is_itinerary else 0

    if is_itinerary:
        system_prompt = (
            f"{get_language_prompt(target_lang)}\n"
            f"You are a smart travel assistant. The user asked for a {days}-day travel itinerary. "
            f"Reply in {target_lang}.Reply with exactly {days} day(s). Start each day with '🗓️ Day X:' and include 3-5 short, emoji-rich bullet points per day. "
            f"Use line breaks between each activity."
        )
    else:
        system_prompt = (
            f"{get_language_prompt(target_lang)}\n"
            f"You are a smart travel assistant. Answer in {target_lang}. Respond briefly and clearly to travel questions using emojis and bullet points. "
            f"Always end your reply with 2–3 follow-up questions written clearly using bullet points (•)."
        )

    messages = [{"role": "system", "content": system_prompt}]
    for item in chat_history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_message})

    api_key = os.getenv("OPENROUTER_API_KEY")
    model= os.getenv("model")
    if not api_key:
        return jsonify({"reply": "⚠️ API key not set. Please check your environment variables."}), 500

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": f"{model}",
        "messages": messages
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers)
        response.raise_for_status()
        full_reply = response.json()["choices"][0]["message"]["content"]
        followup_suggestions = extract_followups(full_reply)
        cleaned_reply = strip_followups_from_reply(full_reply)
    except Exception as e:
        return jsonify({"reply": f"❌ Failed to fetch response: {str(e)}"}), 500

    return jsonify({
        "reply": cleaned_reply,
        "followups": followup_suggestions
    })

@app.route('/download-itinerary', methods=['POST'])
def download_itinerary():
    if 'user_id' not in session:
        return jsonify({"error": "Login required to download itinerary"}), 401

    data = request.json
    itinerary_text = data.get("itinerary", "No itinerary provided.")

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    lines = itinerary_text.split("\n")
    y = height - 40

    for line in lines:
        pdf.drawString(50, y, line.strip())
        y -= 15
        if y < 50:
            pdf.showPage()
            y = height - 40

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="travel_itinerary.pdf",
        mimetype='application/pdf'
    )

def get_language_prompt(lang):
    return f"You must answer only in {lang}. Do not use any other language including English. Never translate, just respond natively.."

if __name__ == '__main__':
    app.run(debug=True)
