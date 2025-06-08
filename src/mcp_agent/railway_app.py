import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class GeofencingTrigger(BaseModel):
    user_id: str
    location: Dict[str, float]
    geofence_id: str
    trigger_type: str
    timestamp: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = {}

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
        "message": "MCP AI Geofencing Marketing System",
        "status": "running",
        "capabilities": [
            "Multi-provider AI (OpenAI, Anthropic, Google)",
            "Geofencing automation",
            "n8n workflow integration",
            "Railway cloud deployment"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "system": "operational"
    }

@app.post("/api/geofencing/trigger")
async def geofencing_trigger(trigger: GeofencingTrigger):
    try:
        response = {
            "trigger_id": f"geo_{trigger.user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "status": "processed",
            "location_analysis": {
                "user_id": trigger.user_id,
                "location": trigger.location,
                "geofence": trigger.geofence_id,
                "action": trigger.trigger_type,
                "timestamp": datetime.utcnow().isoformat()
            },
            "ai_recommendations": {
                "campaign_type": "location_based_offer",
                "urgency": "high" if trigger.trigger_type == "enter" else "medium",
                "channels": ["mobile_push", "email", "dooh"]
            }
        }
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/chat")
async def ai_chat(request: AIRequest):
    try:
        return {
            "response": f"AI response to: {request.message}",
            "provider": request.provider,
            "timestamp": datetime.utcnow().isoformat(),
            "context": request.context
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/n8n/webhook-info")
async def n8n_webhook_info():
    base_url = os.environ.get("RAILWAY_STATIC_URL", "https://your-app.railway.app")
    return {
        "system": "MCP + FastAPI Hybrid",
        "endpoints": {
            "geofencing": f"{base_url}/api/geofencing/trigger",
            "ai_chat": f"{base_url}/api/ai/chat",
            "health": f"{base_url}/health"
        },
        "ready_for_deployment": True
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
