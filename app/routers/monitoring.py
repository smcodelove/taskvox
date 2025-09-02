"""
TasKvox AI - Real-Time Call Monitoring Dashboard
COPY-PASTE THIS COMPLETE FILE
"""
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from typing import List, Dict
import json
import asyncio
from datetime import datetime, timedelta

from app.database import get_db
from app import models, auth
from app.elevenlabs_client import ElevenLabsClient

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        self.active_connections.remove(websocket)
        if user_id in self.user_connections:
            self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_to_user(self, user_id: int, data: dict):
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(data))
                except:
                    pass

    async def broadcast_to_all(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(data))
            except:
                pass

manager = ConnectionManager()

@router.get("", response_class=HTMLResponse)
async def monitoring_dashboard(
    request: Request,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Real-time call monitoring dashboard"""
    
    # Get current statistics
    stats = await get_realtime_stats(current_user.id, db)
    
    # Get active calls
    active_calls = await get_active_calls(current_user.id, db)
    
    # Get recent activity
    recent_activity = await get_recent_activity(current_user.id, db)
    
    return templates.TemplateResponse(
        "monitoring.html",
        {
            "request": request,
            "title": "Real-Time Monitoring - TasKvox AI",
            "user": current_user,
            "stats": stats,
            "active_calls": active_calls,
            "recent_activity": recent_activity
        }
    )

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Send real-time updates every 5 seconds
            stats = await get_realtime_stats(user_id, db)
            active_calls = await get_active_calls(user_id, db)
            
            await manager.send_to_user(user_id, {
                "type": "stats_update",
                "data": {
                    "stats": stats,
                    "active_calls": active_calls,
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            await asyncio.sleep(5)  # Update every 5 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

async def get_realtime_stats(user_id: int, db: Session):
    """Get real-time statistics"""
    now = datetime.now()
    today = now.date()
    
    # Today's calls
    today_calls = db.query(models.Conversation).filter(
        and_(
            models.Conversation.user_id == user_id,
            func.date(models.Conversation.created_at) == today
        )
    ).count()
    
    # Active calls (in progress)
    active_calls = db.query(models.Conversation).filter(
        and_(
            models.Conversation.user_id == user_id,
            models.Conversation.status == "in_progress"
        )
    ).count()
    
    # Completed calls today
    completed_today = db.query(models.Conversation).filter(
        and_(
            models.Conversation.user_id == user_id,
            func.date(models.Conversation.created_at) == today,
            models.Conversation.status == "completed"
        )
    ).count()
    
    # Failed calls today
    failed_today = db.query(models.Conversation).filter(
        and_(
            models.Conversation.user_id == user_id,
            func.date(models.Conversation.created_at) == today,
            models.Conversation.status == "failed"
        )
    ).count()
    
    # Success rate today
    success_rate = (completed_today / today_calls * 100) if today_calls > 0 else 0
    
    # Running campaigns
    running_campaigns = db.query(models.Campaign).filter(
        and_(
            models.Campaign.user_id == user_id,
            models.Campaign.status == "running"
        )
    ).count()
    
    return {
        "today_calls": today_calls,
        "active_calls": active_calls,
        "completed_today": completed_today,
        "failed_today": failed_today,
        "success_rate": round(success_rate, 1),
        "running_campaigns": running_campaigns
    }

async def get_active_calls(user_id: int, db: Session):
    """Get currently active calls"""
    active_calls = db.query(models.Conversation)\
        .join(models.Agent, models.Conversation.agent_id == models.Agent.id)\
        .filter(
            and_(
                models.Conversation.user_id == user_id,
                models.Conversation.status == "in_progress"
            )
        ).all()
    
    return [
        {
            "id": call.id,
            "phone_number": call.phone_number,
            "contact_name": call.contact_name,
            "agent_name": call.agent.name,
            "started_at": call.created_at.isoformat(),
            "duration": int((datetime.now() - call.created_at).total_seconds())
        }
        for call in active_calls
    ]

async def get_recent_activity(user_id: int, db: Session, limit: int = 10):
    """Get recent call activity"""
    recent_calls = db.query(models.Conversation)\
        .join(models.Agent, models.Conversation.agent_id == models.Agent.id)\
        .filter(models.Conversation.user_id == user_id)\
        .order_by(desc(models.Conversation.created_at))\
        .limit(limit).all()
    
    return [
        {
            "id": call.id,
            "phone_number": call.phone_number,
            "contact_name": call.contact_name,
            "agent_name": call.agent.name,
            "status": call.status,
            "duration": call.duration_seconds,
            "created_at": call.created_at.isoformat(),
            "campaign_name": call.campaign.name if call.campaign else "Direct Call"
        }
        for call in recent_calls
    ]

@router.post("/update-call-status")
async def update_call_status(
    conversation_id: int,
    status: str,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Manually update call status (for testing/admin)"""
    
    conversation = db.query(models.Conversation).filter(
        and_(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        )
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation.status = status
    if status == "completed":
        conversation.duration_seconds = int((datetime.now() - conversation.created_at).total_seconds())
    
    db.commit()
    
    # Send real-time update
    await manager.send_to_user(current_user.id, {
        "type": "call_status_update",
        "data": {
            "conversation_id": conversation_id,
            "new_status": status,
            "timestamp": datetime.now().isoformat()
        }
    })
    
    return {"message": "Status updated successfully"}