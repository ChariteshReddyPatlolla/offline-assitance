import logging
import asyncio
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from shared import schemas, models
from shared.database import get_db
from api.routes import chat, approvals, voice, sessions, pdf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OmniAgent API Gateway",
    description="Offline autonomous AI copilot API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core routes
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["Approvals"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF"])


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "version": "2.0.0",
        "features": [
            "chat", "approvals", "voice-stt", "sessions",
            "pdf-explain", "research", "youtube-automation"
        ]
    }


@app.get("/")
def root():
    return {"message": "OmniAgent API is running. See /docs for API reference."}
