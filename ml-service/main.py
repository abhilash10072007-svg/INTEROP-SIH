import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from routers import (
    health,
    fuzzy_match,
    ocr,
    face_match,
    risk_score,
    fraud_check,
    scheme_recommend,
    voice_assistant
)

app = FastAPI(
    title="GovConnect ML Microservice",
    description="Dedicated microservice for identity verification, document OCR, risk analytics, and voice assistance.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register all operational routers
app.include_router(health.router)
app.include_router(fuzzy_match.router)
app.include_router(ocr.router)
app.include_router(face_match.router)
app.include_router(risk_score.router)
app.include_router(fraud_check.router)
app.include_router(scheme_recommend.router)
app.include_router(voice_assistant.router)

DEMO_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GovConnect AI Assistant & Identity Verification</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background-color: #0b132b; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 24px; }
    .container { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; max-width: 1100px; width: 100%; }
    .card { background: #1c2541; border: 1px solid #3a506b; border-radius: 12px; padding: 24px; display: flex; flex-direction: column; }
    h2 { font-size: 1.25rem; font-weight: 600; color: #38bdf8; margin-bottom: 8px; }
    p.subtitle { color: #94a3b8; font-size: 0.875rem; margin-bottom: 16px; }
    
    /* Face Match Styles */
    .field-group { margin-bottom: 14px; }
    label { display: block; font-size: 0.85rem; color: #cbd5e1; margin-bottom: 6px; font-weight: 500; }
    input[type="file"] { width: 100%; padding: 8px; background: #0b132b; border: 1px dashed #475569; border-radius: 6px; color: #94a3b8; font-size: 0.85rem; }
    video { width: 100%; height: 210px; background: #000; border-radius: 8px; object-fit: cover; border: 1px solid #334155; }
    .btn-row { display: flex; gap: 10px; margin-top: 14px; }
    button { cursor: pointer; border: none; border-radius: 6px; font-weight: 600; transition: all 0.2s ease; padding: 10px 16px; font-size: 0.9rem; }
    .btn-blue { background: #2563eb; color: #fff; }
    .btn-blue:hover { background: #1d4ed8; }
    .btn-green { background: #059669; color: #fff; display: flex; align-items: center; gap: 6px; }
    .btn-green:hover { background: #047857; }
    .btn-gray { background: #334155; color: #f8fafc; }
    .btn-gray:hover { background: #475569; }
    #matchResult { margin-top: 14px; font-size: 0.9rem; min-height: 24px; font-weight: 500; }

    /* Chat & Voice Styles */
    .chat-box { background: #0b132b; border: 1px solid #334155; border-radius: 8px; flex: 1; min-height: 280px; max-height: 380px; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; margin-bottom: 14px; }
    .msg { max-width: 82%; padding: 10px 14px; border-radius: 8px; font-size: 0.9rem; line-height: 1.4; word-wrap: break-word; }
    .msg-bot { background: #1e293b; color: #f8fafc; align-self: flex-start; border-left: 3px solid #38bdf8; }
    .msg-user { background: #2563eb; color: #fff; align-self: flex-end; }
    .input-row { display: flex; gap: 8px; }
    input[type="text"] { flex: 1; background: #0b132b; border: 1px solid #334155; border-radius: 6px; padding: 10px 14px; color: #fff; outline: none; }
    input[type="text"]:focus { border-color: #38bdf8; }

    @media (max-width: 768px) {
      .container { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="container">
    
    <!-- Face Match with ID Card Card -->
    <div class="card">
      <h2>Live Identity ID Match</h2>
      <p class="subtitle">Upload official document photo (Aadhaar/PAN/DL) and verify against live selfie stream.</p>

      <div class="field-group">
        <label>1. Official ID Document (Photo):</label>
        <input type="file" id="idPhotoInput" accept="image/*" />
      </div>

      <div class="field-group">
        <label>2. Live Camera Stream:</label>
        <video id="webcam" autoplay playsinline></video>
        <canvas id="snapshotCanvas" style="display:none;"></canvas>
      </div>

      <div class="btn-row">
        <button class="btn-gray" id="startCamBtn" onclick="startCamera()">Start Camera</button>
        <button class="btn-blue" id="verifyBtn" onclick="verifyFaceMatch()">Verify Match</button>
      </div>

      <div id="matchResult"></div>
    </div>

    <!-- AI Voice & Text Assistant Card -->
    <div class="card">
      <h2>Voice & Text Assistant</h2>
      <p class="subtitle">Ask any scheme details or tap Speak to use microphone input.</p>

      <div class="chat-box" id="chatWindow">
        <div class="msg msg-bot">Hello! I am your GovConnect Assistant. How can I help you today?</div>
      </div>

      <div class="input-row">
        <input type="text" id="userInput" placeholder="Ask about schemes, licenses, or status..." onkeydown="handleKeyPress(event)" />
        <button class="btn-blue" onclick="sendTextMessage()">Send</button>
        <button class="btn-green" id="micBtn" onclick="toggleVoiceInput()">🎤 Speak</button>
      </div>
    </div>

  </div>

  <script>
    let mediaStream = null;
    let recognition = null;
    let isListening = false;

    // --- Camera Functions ---
    async function startCamera() {
      try {
        const video = document.getElementById('webcam');
        mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
        video.srcObject = mediaStream;
        document.getElementById('startCamBtn').innerText = "Camera Active";
        document.getElementById('startCamBtn').disabled = true;
      } catch (err) {
        alert("Camera access denied or unavailable: " + err.message);
      }
    }

    async function verifyFaceMatch() {
      const fileInput = document.getElementById('idPhotoInput');
      const resultDiv = document.getElementById('matchResult');
      const video = document.getElementById('webcam');
      const canvas = document.getElementById('snapshotCanvas');

      if (!mediaStream) {
        resultDiv.innerHTML = "<span style='color:#f87171'>Please click 'Start Camera' first.</span>";
        return;
      }

      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      resultDiv.innerHTML = "<span style='color:#38bdf8'>Extracting faces and computing visual similarity...</span>";

      canvas.toBlob(async (selfieBlob) => {
        const formData = new FormData();
        formData.append("selfie", selfieBlob, "selfie.jpg");

        if (fileInput.files.length > 0) {
          formData.append("id_photo", fileInput.files[0], fileInput.files[0].name);
        } else {
          formData.append("id_photo", selfieBlob, "id_document.jpg");
        }

        try {
          const resp = await fetch("/ml/face-match", {
            method: "POST",
            body: formData
          });
          const data = await resp.json();

          if (data.is_matched) {
            resultDiv.innerHTML = `<span style="color:#4ade80">✓ Verified: Match Score ${data.similarity_score} (Confidence: ${data.confidence.toUpperCase()})</span>`;
          } else {
            resultDiv.innerHTML = `<span style="color:#f87171">✗ Not Matched: ${data.message} (Score: ${data.similarity_score})</span>`;
          }
        } catch (err) {
          resultDiv.innerHTML = `<span style="color:#f87171">Error verifying identity: ${err.message}</span>`;
        }
      }, "image/jpeg");
    }

    // --- Voice & Chat Assistant ---
    function appendMessage(text, isUser = false) {
      const win = document.getElementById('chatWindow');
      const bubble = document.createElement('div');
      bubble.className = isUser ? 'msg msg-user' : 'msg msg-bot';
      bubble.innerText = text;
      win.appendChild(bubble);
      win.scrollTop = win.scrollHeight;
    }

    async function sendTextMessage() {
      const input = document.getElementById('userInput');
      const text = input.value.trim();
      if (!text) return;

      appendMessage(text, true);
      input.value = "";

      try {
        const resp = await fetch("/ml/voice-generate-reply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            intent: "query_scheme",
            entities: { query: text },
            backend_data: { user_input: text }
          })
        });
        const data = await resp.json();
        const reply = data.reply_text || "Unable to retrieve information at this moment.";
        appendMessage(reply, false);
        speakText(reply);
      } catch (err) {
        appendMessage("Error communicating with assistant: " + err.message, false);
      }
    }

    function handleKeyPress(e) {
      if (e.key === "Enter") sendTextMessage();
    }

    function speakText(text) {
      if (!('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    }

    function toggleVoiceInput() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        alert("Speech Recognition is not supported by your browser. Please use Chrome or Edge.");
        return;
      }

      const micBtn = document.getElementById('micBtn');

      if (isListening) {
        recognition.stop();
        return;
      }

      recognition = new SpeechRecognition();
      recognition.lang = 'en-IN';
      recognition.interimResults = false;

      recognition.onstart = () => {
        isListening = true;
        micBtn.innerText = "🛑 Listening...";
        micBtn.style.background = "#dc2626";
      };

      recognition.onresult = (event) => {
        const spoken = event.results[0][0].transcript;
        document.getElementById('userInput').value = spoken;
        sendTextMessage();
      };

      recognition.onerror = () => {
        recognition.stop();
      };

      recognition.onend = () => {
        isListening = false;
        micBtn.innerText = "🎤 Speak";
        micBtn.style.background = "#059669";
      };

      recognition.start();
    }
  </script>
</body>
</html>
"""

@app.get("/demo", response_class=HTMLResponse, tags=["Demo"])
def demo_interface():
    return DEMO_HTML

@app.get("/", tags=["Root"])
def root():
    return {
        "service": "GovConnect ML Microservice",
        "status": "online",
        "endpoints": ["/ml/face-match", "/ml/voice-generate-reply", "/ml/ocr-extract", "/demo"]
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)