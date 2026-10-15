import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from engine.nlp import engine
from engine.gemini_agent import generate_gemini_reply
from engine.event_db import (
    init_db,
    get_fixtures,
    get_active_delays,
    set_delay,
    get_facilities
)

app = FastAPI(title="SportDesk - Sports Event Management Assistant", version="1.1.0")

@app.on_event("startup")
def startup_event():
    init_db()

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
def get_root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>SportDesk API is active.</h3>")

class ChatRequest(BaseModel):
    message: str
    api_key: Optional[str] = None

class DelayRequest(BaseModel):
    location: str
    delay_minutes: int
    message: str

class KeyUpdateRequest(BaseModel):
    api_key: str

@app.post("/api/chat")
def handle_chat(req: ChatRequest):
    query = req.message.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Empty query string")
    
    # 1. Try Gemini first if key is present
    gemini_resp = generate_gemini_reply(query, api_key=req.api_key)
    if gemini_resp:
        return gemini_resp

    # 2. Fall back to NLTK similarity engine
    result = engine.predict(query)
    return result

@app.post("/api/config/key")
def update_api_key(req: KeyUpdateRequest):
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="Key cannot be empty")
    
    os.environ["GEMINI_API_KEY"] = key
    
    # Write to .env file
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"GEMINI_API_KEY={key}\n")
    
    return {"status": "success", "message": "Gemini API Key saved and activated successfully!"}

@app.get("/api/fixtures")
def list_fixtures(sport: Optional[str] = None):
    return {"fixtures": get_fixtures(sport)}

@app.get("/api/delays")
def list_delays():
    return {"delays": get_active_delays()}

@app.post("/api/delays")
def report_delay(req: DelayRequest):
    set_delay(req.location, req.delay_minutes, req.message, is_active=True)
    return {"status": "success", "message": f"Delay registered for {req.location}"}

@app.get("/api/facilities")
def list_facilities(query: Optional[str] = None):
    return {"facilities": get_facilities(query)}

@app.get("/api/status")
def system_status():
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy",
        "has_gemini_key": has_gemini,
        "engine": "Gemini 2.5 Flash + SQLite Ground Truth" if has_gemini else "NLTK + TF-IDF (Fallback)",
        "database": "SQLite (Live Fixtures & Delays)",
        "cached_patterns": len(engine.corpus_patterns)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
