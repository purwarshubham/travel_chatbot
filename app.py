import os
import re
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

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

    itinerary_match = re.search(r'(\d+)[-\s]?day', user_message.lower())
    is_itinerary = bool(itinerary_match)
    days = int(itinerary_match.group(1)) if is_itinerary else 0

    if is_itinerary:
        system_prompt = (
            f"You are a smart travel assistant. The user asked for a {days}-day travel itinerary. "
            f"Reply with exactly {days} day(s). Start each day with '🗓️ Day X:' and include 3-5 short, emoji-rich bullet points per day. "
            f"Use line breaks between each activity."
        )
    else:
        system_prompt = (
            "You are a smart travel assistant. Respond briefly and clearly to travel questions using emojis and bullet points. "
            "Always end your reply with 2–3 follow-up questions written clearly using bullet points (•). Example:\n• What’s the best time to visit?\n• Any unique dishes I should try?\n• budget for a trip?\n• Do I need a visa?"
            "You are a helpful travel assistant. After every answer, provide 2–3 relevant follow-up questions using clear bullet points like:\n- Question 1?\n- Question 2?\n- Question 3?"
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

if __name__ == '__main__':
    app.run(debug=True)
