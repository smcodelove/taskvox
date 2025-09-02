# FILE: app/routers/playback.py
# COPY-PASTE THIS COMPLETE FILE

"""
TasKvox AI - Call Recording Playback System
Built-in Audio Player with Transcript Sync
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
import json
import httpx
from datetime import datetime, timedelta

from app.database import get_db
from app import models, auth
from app.elevenlabs_client import ElevenLabsClient

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
async def playback_dashboard(
    request: Request,
    search: Optional[str] = Query(None),
    agent_filter: Optional[int] = Query(None),
    campaign_filter: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Call Recording Playback Dashboard"""
    
    # Base query for conversations with recordings
    query = db.query(models.Conversation)\
        .options(joinedload(models.Conversation.agent))\
        .options(joinedload(models.Conversation.campaign))\
        .filter(
            and_(
                models.Conversation.user_id == current_user.id,
                models.Conversation.external_conversation_id.isnot(None),  # Has recording
                models.Conversation.status == "completed"
            )
        )
    
    # Apply filters
    if search:
        query = query.filter(
            models.Conversation.phone_number.ilike(f"%{search}%") |
            models.Conversation.contact_name.ilike(f"%{search}%")
        )
    
    if agent_filter:
        query = query.filter(models.Conversation.agent_id == agent_filter)
    
    if campaign_filter:
        query = query.filter(models.Conversation.campaign_id == campaign_filter)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(models.Conversation.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(models.Conversation.created_at < to_date)
        except ValueError:
            pass
    
    # Get recordings
    recordings = query.order_by(desc(models.Conversation.created_at)).limit(50).all()
    
    # Get filter options
    agents = db.query(models.Agent).filter(models.Agent.user_id == current_user.id).all()
    campaigns = db.query(models.Campaign).filter(models.Campaign.user_id == current_user.id).all()
    
    # Statistics
    total_recordings = query.count()
    total_duration = sum(r.duration_seconds or 0 for r in recordings)
    
    return templates.TemplateResponse(
        "playback.html",
        {
            "request": request,
            "title": "Call Recordings - TasKvox AI",
            "user": current_user,
            "recordings": recordings,
            "agents": agents,
            "campaigns": campaigns,
            "stats": {
                "total_recordings": total_recordings,
                "total_duration": total_duration,
                "avg_duration": (total_duration / total_recordings) if total_recordings > 0 else 0
            },
            "filters": {
                "search": search or "",
                "agent_filter": agent_filter or "",
                "campaign_filter": campaign_filter or "",
                "date_from": date_from or "",
                "date_to": date_to or ""
            }
        }
    )

@router.get("/{conversation_id}/audio-url")
async def get_audio_url(
    conversation_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get audio streaming URL for a conversation"""
    
    conversation = db.query(models.Conversation).filter(
        and_(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id,
            models.Conversation.external_conversation_id.isnot(None)
        )
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if not current_user.voice_api_key:
        raise HTTPException(status_code=400, detail="Voice AI API key not configured")
    
    try:
        client = ElevenLabsClient(current_user.voice_api_key)
        result = await client.get_conversation_audio(conversation.external_conversation_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail="Audio not available")
        
        return {
            "audio_url": result["audio_url"],
            "conversation_id": conversation_id,
            "duration": conversation.duration_seconds,
            "contact_name": conversation.contact_name,
            "phone_number": conversation.phone_number
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audio: {str(e)}")

@router.get("/{conversation_id}/stream")
async def stream_audio(
    conversation_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Stream audio directly through our server"""
    
    conversation = db.query(models.Conversation).filter(
        and_(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id,
            models.Conversation.external_conversation_id.isnot(None)
        )
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    if not current_user.voice_api_key:
        raise HTTPException(status_code=400, detail="Voice AI API key not configured")
    
    try:
        client = ElevenLabsClient(current_user.voice_api_key)
        result = await client.get_conversation_audio(conversation.external_conversation_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail="Audio not available")
        
        audio_url = result["audio_url"]
        
        # Stream audio through our server
        async def generate_audio():
            async with httpx.AsyncClient() as http_client:
                async with http_client.stream("GET", audio_url) as response:
                    async for chunk in response.aiter_bytes(8192):
                        yield chunk
        
        return StreamingResponse(
            generate_audio(),
            media_type="audio/mpeg",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Disposition": f"inline; filename=\"call_{conversation_id}.mp3\""
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stream audio: {str(e)}")

@router.get("/{conversation_id}/waveform")
async def get_waveform_data(
    conversation_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Generate waveform data for audio visualization"""
    
    conversation = db.query(models.Conversation).filter(
        and_(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        )
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Generate sample waveform data (in real implementation, you'd analyze the actual audio)
    duration = conversation.duration_seconds or 60
    sample_rate = 44100
    samples_per_pixel = 512
    
    # Generate realistic waveform data
    import random
    import math
    
    pixels = int(duration * sample_rate / samples_per_pixel)
    waveform_data = []
    
    for i in range(pixels):
        # Create more realistic waveform with speech patterns
        base_amplitude = 0.3 + 0.4 * random.random()
        
        # Add some speech-like patterns
        if i % 20 < 10:  # Simulate speech bursts
            amplitude = base_amplitude * (0.8 + 0.4 * math.sin(i * 0.1))
        else:  # Simulate pauses
            amplitude = base_amplitude * 0.2
        
        # Add some randomness
        amplitude *= (0.7 + 0.6 * random.random())
        amplitude = min(1.0, max(0.0, amplitude))
        
        waveform_data.append(amplitude)
    
    return {
        "waveform": waveform_data,
        "duration": duration,
        "sample_rate": sample_rate,
        "pixels": pixels
    }

@router.post("/{conversation_id}/add-marker")
async def add_playback_marker(
    conversation_id: int,
    timestamp: float,
    note: str,
    marker_type: str = "note",
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Add a marker/note to a specific timestamp in the recording"""
    
    conversation = db.query(models.Conversation).filter(
        and_(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        )
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Store marker in conversation metadata (you might want a separate markers table)
    metadata = json.loads(conversation.metadata or "{}")
    if "markers" not in metadata:
        metadata["markers"] = []
    
    marker = {
        "id": len(metadata["markers"]) + 1,
        "timestamp": timestamp,
        "note": note,
        "type": marker_type,
        "created_at": datetime.now().isoformat(),
        "created_by": current_user.email
    }
    
    metadata["markers"].append(marker)
    conversation.metadata = json.dumps(metadata)
    
    db.commit()
    
    return {"message": "Marker added successfully", "marker": marker}

@router.get("/{conversation_id}/markers")
async def get_playback_markers(
    conversation_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get all markers for a conversation"""
    
    conversation = db.query(models.Conversation).filter(
        and_(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        )
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    metadata = json.loads(conversation.metadata or "{}")
    markers = metadata.get("markers", [])
    
    return {"markers": markers}

@router.get("/api/recent")
async def get_recent_recordings(
    limit: int = Query(10, le=50),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get recent recordings for quick access"""
    
    recordings = db.query(models.Conversation)\
        .options(joinedload(models.Conversation.agent))\
        .options(joinedload(models.Conversation.campaign))\
        .filter(
            and_(
                models.Conversation.user_id == current_user.id,
                models.Conversation.external_conversation_id.isnot(None),
                models.Conversation.status == "completed"
            )
        )\
        .order_by(desc(models.Conversation.created_at))\
        .limit(limit).all()
    
    return [
        {
            "id": r.id,
            "contact_name": r.contact_name,
            "phone_number": r.phone_number,
            "agent_name": r.agent.name if r.agent else "Unknown",
            "campaign_name": r.campaign.name if r.campaign else "Direct Call",
            "duration": r.duration_seconds,
            "created_at": r.created_at.isoformat(),
            "has_transcript": bool(r.transcript)
        }
        for r in recordings
    ]