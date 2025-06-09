import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class AIRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = {}
    provider: Optional[str] = "auto"

app = FastAPI(
    title="MCP AI Geofencing System",
    description="AI-powered geofencing marketing automation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "🚀 AI Geofencing Marketing System LIVE!",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/chat")
async def chat(request: AIRequest):
    try:
        return {
            "response": f"Hello! I'm your geofencing expert assistant. You asked: {request.message}",
            "session_id": request.context.get("session_id", "default"),
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Vercel expects this handler
handler = app
