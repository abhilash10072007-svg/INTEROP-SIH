from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Interactive Demo"])

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GovConnect AI Assistant & Face Match Demo</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; max-width: 1100px; margin: 0 auto; }
        .card { background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }
        h2 { margin-top: 0; color: #38bdf8; font-size: 1.25rem; }
        video, canvas { width: 100%; max-height: 240px; border-radius: 8px; background: #000; object-fit: cover; }
        button { background: #2563eb; color: white; border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; margin-top: 8px; }
        button:hover { background: #1d4ed8; }
        .chat-box { height: 260px; overflow-y: auto; background: #0b1329; border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 8px; font-size: 0.9rem; }
        .msg { padding: 8px 12px; border-radius: 8px; max-width: 80%; }
        .msg.user { background: #2563eb; align-self: flex-end; }
        .msg.bot { background: #334155; align-self: flex-start; }
        input[type="text"] { width: calc(100% - 100px); padding: 10px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: white; }
        .status-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; margin-top: 8px; }
        .verified { background: #166534; color: #86efac; }
        .failed { background: #991b1b; color: #fca5a5; }
    </style>
</head>
<body>
    <div class="grid">
        <!-- Module 1: Camera Face Verification -->
        <div class="card">
            <h2>Live Identity Face Match</h2>
            <p style="font-size: 0.85rem; color: #94a3b8;">Verifies live selfie against database photo.</p>
            <video id="webcam" autoplay playsinline></video>
            <canvas id="canvas" style="display:none;"></canvas>
            <div style="display:flex; gap:10px; margin-top:10px;">
                <button onclick="startCamera()">Start Camera</button>
                <button onclick="captureAndVerify()">Verify Identity</button>
            </div>
            <div id="match-result" style="margin-top:12px;"></div>
        </div>

        <!-- Module 2: Chatbot & Voice Assistant -->
        <div class="card">
            <h2>Voice & Text Assistant</h2>
            <p style="font-size: 0.85rem; color: #94a3b8;">Ask scheme queries or speak into your microphone.</p>
            <div class="chat-box" id="chat">
                <div class="msg bot">Hello! I am your GovConnect Assistant. How can I help you today?</div>
            </div>
            <div style="display:flex; gap:8px; margin-top:10px;">
                <input type="text" id="userInput" placeholder="Ask about schemes, license, or loans..." onkeypress="if(event.key==='Enter') sendText()">
                <button onclick="sendText()">Send</button>
                <button onclick="startVoice()" id="micBtn" style="background:#059669;">🎤 Speak</button>
            </div>
        </div>
    </div>

    <script>
        let stream = null;
        async function startCamera() {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: true });
                document.getElementById('webcam').srcObject = stream;
            } catch (err) {
                alert("Camera access denied or unavailable.");
            }
        }

        async function captureAndVerify() {
            const video = document.getElementById('webcam');
            const canvas = document.getElementById('canvas');
            canvas.width = video.videoWidth || 320;
            canvas.height = video.videoHeight || 240;
            canvas.getContext('2d').drawImage(video, 0, 0);

            canvas.toBlob(async (blob) => {
                const formData = new FormData();
                formData.append('selfie', blob, 'selfie.jpg');
                formData.append('id_photo', blob, 'id_photo.jpg');

                const res = await fetch('/ml/face-match', { method: 'POST', body: formData });
                const data = await res.json();
                
                const resultDiv = document.getElementById('match-result');
                if (data.auto_verified) {
                    resultDiv.innerHTML = `<span class="status-badge verified">Verified: Similarity Score ${data.similarity_score} (Confidence: ${data.confidence})</span>`;
                } else {
                    resultDiv.innerHTML = `<span class="status-badge failed">Not Matched: Confidence low</span>`;
                }
            }, 'image/jpeg');
        }

        function appendMessage(text, role) {
            const box = document.getElementById('chat');
            const msg = document.createElement('div');
            msg.className = `msg ${role}`;
            msg.innerText = text;
            box.appendChild(msg);
            box.scrollTop = box.scrollHeight;
        }

        async function sendText() {
            const input = document.getElementById('userInput');
            const text = input.value.trim();
            if (!text) return;
            appendMessage(text, 'user');
            input.value = '';

            const res = await fetch('/ml/voice-generate-reply', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    intent: "user_query",
                    entities: { query: text },
                    backend_data: { context: "GovConnect Platform Assistance" }
                })
            });
            const data = await res.json();
            appendMessage(data.reply_text, 'bot');
            speakText(data.reply_text);
        }

        function startVoice() {
            const recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!recognition) return alert("Web Speech API is not supported in this browser.");
            
            const recognizer = new recognition();
            recognizer.lang = 'en-US';
            document.getElementById('micBtn').style.background = '#dc2626';

            recognizer.onresult = (event) => {
                document.getElementById('micBtn').style.background = '#059669';
                const speechText = event.results[0][0].transcript;
                document.getElementById('userInput').value = speechText;
                sendText();
            };

            recognizer.onerror = () => {
                document.getElementById('micBtn').style.background = '#059669';
            };

            recognizer.start();
        }

        function speakText(text) {
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                window.speechSynthesis.speak(utterance);
            }
        }
    </script>
</body>
</html>
"""

@router.get("/demo", response_class=HTMLResponse)
def get_demo():
    return HTML_CONTENT