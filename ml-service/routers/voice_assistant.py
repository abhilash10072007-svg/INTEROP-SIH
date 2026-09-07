from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from core.groq_client import groq_client
import json

router = APIRouter(prefix="/ml", tags=["Voice Assistant"])

class VoiceReplyReq(BaseModel):
    intent: str
    entities: dict
    backend_data: dict

@router.post("/voice-transcribe-intent")
async def voice_transcribe(file: UploadFile = File(...)):
    user_text = "What schemes can I apply for?"
    if groq_client:
        try:
            transcription = groq_client.audio.transcriptions.create(
                file=(file.filename, await file.read()),
                model="whisper-large-v3"
            )
            user_text = transcription.text
        except Exception:
            pass

    return {
        "transcribed_text": user_text,
        "detected_intent": "scheme_query",
        "extracted_entities": {"query": user_text}
    }

@router.post("/voice-generate-reply")
def voice_reply(req: VoiceReplyReq):
    user_query = req.entities.get("query") or req.backend_data.get("user_input") or req.intent

    if groq_client:
        # Pass reasoning_format='hidden' and reasoning_effort='none' to eliminate think blocks
        for model_id in ["qwen/qwen3.6-27b", "openai/gpt-oss-20b", "groq/compound-mini"]:
            try:
                resp = groq_client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are the GovConnect Assistant for Indian government services. Answer the citizen directly in 2 sentences referencing Indian portals (e.g., Parivahan Sewa, RTO, NSP, PM SVANidhi) where relevant."
                        },
                        {
                            "role": "user",
                            "content": str(user_query)
                        }
                    ],
                    max_tokens=250,
                    reasoning_format="hidden",
                    extra_body={"reasoning_effort": "none"}
                )
                answer = resp.choices[0].message.content.strip()
                if answer:
                    return {"reply_text": answer}
            except Exception:
                # Fallback if reasoning parameters aren't supported on a specific model
                try:
                    resp = groq_client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "user", "content": f"Answer concisely in 2 sentences: {user_query}"}
                        ],
                        max_tokens=250
                    )
                    raw = resp.choices[0].message.content
                    if "</think>" in raw:
                        raw = raw.split("</think>")[-1]
                    ans = raw.strip()
                    if ans:
                        return {"reply_text": ans}
                except Exception:
                    continue

    return {
        "reply_text": "I can help answer any questions about government welfare schemes, licenses, and public services."
    }