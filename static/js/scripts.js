document.getElementById('theme-switch').addEventListener('change', function () {
  document.body.classList.toggle('dark-mode');
});

document.getElementById("user-input").addEventListener("keydown", function (e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

function sendMessage(text = null) {
  const input = document.getElementById('user-input');
  const message = text || input.value.trim();
  if (!message) return;

  appendMessage('user', message);
  input.value = '';
  input.disabled = true;
  showTyping();

  const history = [];
  const messages = document.querySelectorAll('.message');
  messages.forEach(msg => {
    const role = msg.classList.contains('user') ? 'user' : 'assistant';
    const content = msg.querySelector('.text')?.innerText.trim();
    if (content) history.push({ role, content });
  });

  fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history })
  })
    .then(res => res.json())
    .then(data => {
      hideTyping();
      appendMessage('bot', data.reply, data.followups);
      input.disabled = false;
      input.focus();
    })
    .catch(err => {
      hideTyping();
      appendMessage('bot', '⚠️ Something went wrong.');
      input.disabled = false;
      input.focus();
    });
}

function showTyping() {
  const chatBox = document.getElementById('chat-box');
  const typingDiv = document.createElement('div');
  typingDiv.className = 'message bot typing';
  typingDiv.id = 'typing-indicator';
  typingDiv.innerHTML = `
    <img class="avatar" src="/static/bot.png">
    <div class="text typing-dots"><span></span><span></span><span></span></div>`;
  chatBox.appendChild(typingDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function hideTyping() {
  const typing = document.getElementById('typing-indicator');
  if (typing) typing.remove();
}

function appendMessage(sender, text, followups = []) {
  const chatBox = document.getElementById('chat-box');
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}`;

  let formattedText = text;

  // 🧠 Remove follow-up questions from text if they exist
  if (sender === 'bot' && followups && followups.length) {
    const escapedFollowups = followups.map(q =>
      q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    );
    const followupRegex = new RegExp(`(?:^|\\n)[•\\-]?\\s*(${escapedFollowups.join('|')})`, 'gi');
    formattedText = text.replace(followupRegex, '').trim();
  }

  if (sender === 'bot') {
    const isItinerary = /🗓️ Day \d:/g.test(formattedText);
    if (isItinerary) {
      formattedText = formattedText
        .replace(/🗓️ Day \d:/g, match => `<h4>${match}</h4>`)
        .replace(/\n{2,}/g, '<br>')
        .replace(/\n/g, '</div><div style="margin-bottom: 8px;">')
        .replace(/^/, '<div style="margin-bottom: 8px;">')
        .concat('</div>');

      // Add a download button below the itinerary
      formattedText += `
        <div style="margin-top: 12px;">
          <button class="download-btn" onclick="downloadPDF(\`${text}\`)">
            📄 Download Itinerary as PDF
          </button>
        </div>`;
    } else {
      formattedText = formattedText.replace(/\n/g, '<br>');
    }

    // 🧠 Create follow-up buttons only
    if (followups.length) {
      const old = document.querySelectorAll('.followup-container');
      old.forEach(e => e.remove());

      const buttons = followups.map(q =>
        `<button class="followup-btn" onclick="sendMessage('${q}')">${q}</button>`
      ).join('');
      formattedText += `<div class="followup-container">${buttons}</div>`;
    }
  }

  msgDiv.innerHTML = `
    <img class="avatar" src="/static/${sender}.png">
    <div class="text">${formattedText}</div>`;
  chatBox.appendChild(msgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// download Itinerary option

function downloadPDF(itineraryText) {
  fetch('/download-itinerary', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ itinerary: itineraryText })
  })
  .then(res => res.blob())
  .then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'travel_itinerary.pdf';
    a.click();
    window.URL.revokeObjectURL(url);
  });
}