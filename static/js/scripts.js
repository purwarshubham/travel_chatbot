// Switch logic
document.getElementById('theme-switch').addEventListener('change', function () {
  document.body.classList.toggle('dark-mode');
});

// Add logic for Enter key
document.getElementById("user-input").addEventListener("keydown", function (e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault(); // prevent newline
    sendMessage();
  }
});

function sendMessage() {
  const input = document.getElementById('user-input');
  const message = input.value.trim();
  if (!message) return;

  appendMessage('user', message);
  input.value = ''; // clear input
  input.disabled = true; // temporarily disable to prevent double send
  showTyping(); // optional: show typing animation
  fetch('/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message})
  })
  .then(res => res.json())
  .then(
      data => {
        hideTyping();
        appendMessage('bot', data.reply);
        input.disabled = false;
        input.focus(); // return focus to input
      })
  .catch(err => {
    console.error('Error:', err);
    hideTyping();
    appendMessage('bot', '⚠️ Something went wrong. Please try again.');
    input.disabled = false;
    input.focus();
  });
}

// Show Typing
function showTyping() {
  const chatBox = document.getElementById('chat-box');
  const typingDiv = document.createElement('div');
  typingDiv.className = 'message bot typing';
  typingDiv.id = 'typing-indicator';
  typingDiv.innerHTML = `
    <img class="avatar" src="/static/bot.png">
    <div class="text typing-dots">
      <span></span><span></span><span></span>
    </div>`;
  chatBox.appendChild(typingDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function hideTyping() {
  const typing = document.getElementById('typing-indicator');
  if (typing) typing.remove();
}

function appendMessage(sender, text) {
  const chatBox = document.getElementById('chat-box');
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}`;

  let formattedText = text;

  if (sender === 'bot') {
    const isItinerary = /🗓️ Day \d:/g.test(text);

    if (isItinerary) {
      // Format day headings and each activity with spacing
      formattedText = text
        .replace(/🗓️ Day \d:/g, match => `<h4>${match}</h4>`)
        .replace(/\n{2,}/g, '<br>')
        .replace(/\n/g, '</div><div style="margin-bottom: 8px;">')
        .replace(/^/, '<div style="margin-bottom: 8px;">')
        .concat('</div>');
    } else {
      // For general responses, preserve line breaks and bullets
      formattedText = text.replace(/\n/g, '<br>');
    }
  }

  msgDiv.innerHTML = `
    <img class="avatar" src="/static/${sender}.png">
    <div class="text">${formattedText}</div>`;
  chatBox.appendChild(msgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}