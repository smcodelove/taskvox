"""
TasKvox AI - Main FastAPI Application
Updated with Settings and History routes
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from app.routers import elevenlabs_webhooks, plivo_webhooks

# Load environment variables
load_dotenv()

# Import routers
from app.routers import auth, agents, campaigns, dashboard, settings, history, reports, monitoring, playback

# Import database
from app.database import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="TasKvox AI",
    description="Conversational AI Dashboard for Voice Campaigns",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="", tags=["Dashboard"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])
app.include_router(settings.router, prefix="/settings", tags=["Settings"])
app.include_router(history.router, prefix="/history", tags=["History"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
app.include_router(playback.router, prefix="/playback", tags=["Playback"])
app.include_router(elevenlabs_webhooks.router, prefix="", tags=["ElevenLabs Webhooks"])
app.include_router(plivo_webhooks.router, prefix="", tags=["Plivo Webhooks"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Landing page - redirect to login"""
    return RedirectResponse(url="/auth/login", status_code=302)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "taskvox-ai"}

@app.get("/health/db")
async def database_health_check():
    """Database health check"""
    from app.database import test_connection
    if test_connection():
        return {"status": "healthy", "database": "connected"}
    else:
        return {"status": "unhealthy", "database": "disconnected"}

@app.get("/health/api")
async def api_health_check():
    """ElevenLabs API health check"""
    try:
        from app.elevenlabs_client import ElevenLabsClient
        
        # Use a test API key or get from environment
        test_api_key = os.getenv("DEFAULT_ELEVENLABS_API_KEY")
        if not test_api_key:
            return {"status": "unknown", "api": "no test key configured"}
        
        client = ElevenLabsClient(test_api_key)
        result = await client.test_connection()
        
        if result["success"]:
            return {"status": "healthy", "api": "connected"}
        else:
            return {"status": "unhealthy", "api": "connection failed"}
            
    except Exception as e:
        return {"status": "error", "api": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )