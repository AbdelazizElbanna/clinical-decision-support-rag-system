import os
import json
import re
import base64
import asyncio
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import edge_tts

from database import engine, Base, get_db
from models import User
from auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

from pipeline import run_pipeline, run_pipeline_stream
from weather_service import resolve_governorate, fetch_weather
from config import CITIES_JSON_PATH
from groq import Groq
from groq_router import groq_router

# Create database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MedLens AI - Context-Aware Health RAG", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    age: Optional[int] = None
    gender: Optional[str] = None   # "male" | "female" | "other"
    notes: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserProfileUpdate(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    notes: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    chat_summary: Optional[Dict[str, Any]] = None  # Working memory from localStorage
    is_voice: bool = False  # True when query came from STT transcription


# --- AUTHENTICATION ENDPOINTS ---

@app.post("/api/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        age=user.age,
        gender=user.gender,
        notes=user.notes
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(
        data={"sub": new_user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "terms_accepted": new_user.terms_accepted,
        "profile": _user_profile(new_user)
    }


@app.post("/api/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": db_user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "terms_accepted": db_user.terms_accepted,
        "profile": _user_profile(db_user)
    }


@app.get("/api/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "terms_accepted": current_user.terms_accepted,
        "profile": _user_profile(current_user)
    }


@app.put("/api/me/profile")
def update_profile(
    update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if update.age is not None:
        current_user.age = update.age
    if update.gender is not None:
        current_user.gender = update.gender
    if update.notes is not None:
        current_user.notes = update.notes
    db.commit()
    db.refresh(current_user)
    return {"status": "success", "profile": _user_profile(current_user)}


@app.post("/api/accept-terms")
def accept_terms(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.terms_accepted = True
    db.commit()
    return {"status": "success", "terms_accepted": True}


def _user_profile(user: User) -> dict:
    return {
        "username": user.username,
        "email": user.email,
        "age": user.age,
        "gender": user.gender,
        "notes": user.notes,
    }


# --- RAG ENDPOINTS ---

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


# --- VOICE ENDPOINTS ---

@app.post("/api/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Transcribe an audio file using Groq Whisper (Arabic-optimised).
    Accepts any format Whisper supports (webm/opus from MediaRecorder, mp3, wav…).
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(400, "Empty audio file received")

    try:
        # Reuse the project's key-manager to get a live Groq client
        api_key = groq_router._get_available_key()
        client = groq_router._get_client(api_key)
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=(file.filename or "audio.webm", audio_bytes, file.content_type or "audio/webm"),
            language="ar",
        )
        return {"text": transcription.text}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, f"Transcription failed: {e}")


_AR_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]')
_ALPHA_RE = re.compile(r'[a-zA-Z\u0600-\u06FF]')


def _word_lang(word: str) -> str:
    return 'ar' if _AR_RE.search(word) else 'en'


def _dominant_lang(text: str) -> str:
    arabic = len(_AR_RE.findall(text))
    total  = len(_ALPHA_RE.findall(text))
    if total == 0:
        return 'ar'
    return 'ar' if arabic / total >= 0.15 else 'en'


def _split_lang_segments(text: str) -> list:
    words = text.split()
    if not words:
        return []
    raw = []
    cur_lang = _word_lang(words[0])
    buf = [words[0]]
    for w in words[1:]:
        lang = _word_lang(w)
        if lang == cur_lang:
            buf.append(w)
        else:
            raw.append((' '.join(buf), cur_lang))
            buf = [w]
            cur_lang = lang
    raw.append((' '.join(buf), cur_lang))
    # Merge isolated short English runs back into preceding Arabic segment
    merged = []
    for seg_text, seg_lang in raw:
        if seg_lang == 'en' and len(seg_text.split()) <= 2 and merged and merged[-1][1] == 'ar':
            merged[-1] = (merged[-1][0] + ' ' + seg_text, 'ar')
        else:
            merged.append((seg_text, seg_lang))
    return merged


def _clean_for_tts(text: str) -> str:
    """Strip markdown/structural noise from LLM output before TTS synthesis."""
    # 1. Remove numbered section-header lines (e.g. "1. Short Answer:", "2. **Evidence:**")
    #    Matches any line: starts with digit+period, ends with colon (possibly with bold markers).
    text = re.sub(r'^\s*\d+\.\s+\*{0,2}[^\n]{1,80}\*{0,2}\s*:\s*$', '', text, flags=re.MULTILINE)
    # 2. Remove citation tags: [Source 1], (Source 2, 3) …
    text = re.sub(r'[\[\(][Ss]ources?\s*[\d\s,&and]+[\]\)]', '', text)
    # 3. Bold/italic markers
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', text)
    # 4. Markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # 5. Bullet list markers
    text = re.sub(r'^\s*[-*•]\s+', '', text, flags=re.MULTILINE)
    # 6. URLs
    text = re.sub(r'https?://\S+', '', text)
    # 7. Leftover empty brackets
    text = re.sub(r'\[\s*\]|\(\s*\)', '', text)
    # 8. Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    return text.strip()


@app.post("/api/tts")
async def text_to_speech(
    req: dict,
    current_user: User = Depends(get_current_user)
):
    """Convert text to speech.
    Returns JSON: {audio: base64 MP3, words: [{word, start_ms, end_ms}]}
    Uses ar-EG-SalmaNeural for Arabic, en-US-JennyNeural for English segments.
    """
    raw_text = (req.get("text") or "").strip()
    if not raw_text:
        raise HTTPException(400, "Text cannot be empty")

    cleaned = _clean_for_tts(raw_text)
    if not cleaned:
        raise HTTPException(400, "No speakable text after cleaning")

    ar_voice = "ar-EG-SalmaNeural"
    en_voice = "en-US-JennyNeural"

    dom = _dominant_lang(cleaned)
    segments = [(cleaned, 'en')] if dom == 'en' else _split_lang_segments(cleaned)

    audio_parts: list[bytes] = []
    words: list[dict] = []
    cumulative_ms = 0.0

    for seg_text, seg_lang in segments:
        if not seg_text.strip():
            continue
        voice = ar_voice if seg_lang == 'ar' else en_voice
        communicate = edge_tts.Communicate(text=seg_text, voice=voice)
        seg_audio: list[bytes] = []
        seg_words: list[dict] = []
        last_end_ms = 0.0
        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    seg_audio.append(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    s_ms = chunk["offset"] / 10_000
                    d_ms = chunk["duration"] / 10_000
                    seg_words.append({
                        "word":     chunk["text"],
                        "start_ms": round(cumulative_ms + s_ms, 1),
                        "end_ms":   round(cumulative_ms + s_ms + d_ms, 1),
                    })
                    last_end_ms = max(last_end_ms, s_ms + d_ms)
        except Exception:
            import traceback; traceback.print_exc()
            continue

        audio_parts.extend(seg_audio)
        words.extend(seg_words)
        cumulative_ms += last_end_ms + 80  # 80 ms gap between segments

    if not audio_parts:
        raise HTTPException(500, "TTS generation produced no audio")

    audio_b64 = base64.b64encode(b"".join(audio_parts)).decode()
    return {"audio": audio_b64, "words": words}


@app.post("/api/query")
async def query_rag(
    req: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    if not current_user.terms_accepted:
        raise HTTPException(status_code=403, detail="Terms of use must be accepted first")
    if not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    patient_profile = _user_profile(current_user)

    try:
        result = await run_pipeline(
            user_query=req.query,
            patient_profile=patient_profile,
            chat_summary=req.chat_summary or {}
        )
        return result
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, str(e))



@app.post("/api/query/stream")
async def query_rag_stream(
    req: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    if not current_user.terms_accepted:
        raise HTTPException(status_code=403, detail="Terms of use must be accepted first")
    if not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    patient_profile = _user_profile(current_user)
    
    return StreamingResponse(
        run_pipeline_stream(
            user_query=req.query,
            patient_profile=patient_profile,
            chat_summary=req.chat_summary or {},
            is_voice=req.is_voice
        ),
        media_type="text/event-stream"
    )

@app.get("/api/weather/{governorate}")
async def weather_for_governorate(governorate: str):
    gov = resolve_governorate(governorate)
    if not gov:
        raise HTTPException(404, f"Governorate '{governorate}' not found")
    weather = await fetch_weather(gov["lat"], gov["lon"])
    return {
        "governorate_en": gov["governorate_en"],
        "governorate_ar": gov["governorate_ar"],
        "lat": gov["lat"], "lon": gov["lon"],
        "weather": weather
    }


@app.get("/api/governorates")
async def list_governorates():
    with open(CITIES_JSON_PATH, encoding="utf-8") as f:
        cities = json.load(f)
    return [{"id": c["id"], "en": c["governorate_en"], "ar": c["governorate_ar"],
             "lat": c["lat"], "lon": c["lon"]} for c in cities]


# Serve React static build - MUST be last
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
