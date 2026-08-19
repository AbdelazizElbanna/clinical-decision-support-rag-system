import os
import json
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

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
            chat_summary=req.chat_summary or {}
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
