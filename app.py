import os
import re
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

load_dotenv()
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def extract_followups(text):
    # Match lines that are follow-up questions (bullets or standalone)
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
            f"Answer in {target_lang}. Always end your reply with 2–3 follow-up questions written clearly using bullet points (•). Example:\n• What’s the best time to visit?\n• Any unique dishes I should try?\n• budget for a trip?\n• Do I need a visa?"
            f"Answer in {target_lang}. You are a helpful travel assistant. After every answer, provide 2–3 relevant follow-up questions using clear bullet points like:\n- Question 1?\n- Question 2?\n- Question 3?"
            "Do not repeat the heading or mix with other text."
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
        # Remove follow-up section from reply before displaying
        cleaned_reply = strip_followups_from_reply(full_reply)
    except Exception as e:
        return jsonify({"reply": f"❌ Failed to fetch response: {str(e)}"}), 500

    return jsonify({
        "reply": cleaned_reply,
        "followups": followup_suggestions
    })

@app.route('/download-itinerary', methods=['POST'])
def download_itinerary():
    data = request.json
    itinerary_text = data.get("itinerary", "No itinerary provided.")

    # Create PDF in memory
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
