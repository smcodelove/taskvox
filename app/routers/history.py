# FILE: app/routers/history.py
# REPLACE YOUR ENTIRE app/routers/history.py WITH THIS CORRECTED VERSION

"""
TasKvox AI - Enhanced History Router with Recording & Transcript Download
Added features: Recording download, Transcript export, Advanced analytics
"""
import os
import csv
import json
import tempfile
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, Response
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, or_, func
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

from app.database import get_db
from app import models, schemas, auth
from app.elevenlabs_client import ElevenLabsClient

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
async def history_page(
    request: Request,
    page: int = Query(1, ge=1),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    campaign_filter: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Enhanced call history page with advanced filtering"""
    
    # Items per page
    per_page = 20
    offset = (page - 1) * per_page
    
    # Base query
    query = db.query(models.Conversation)\
        .options(joinedload(models.Conversation.agent))\
        .options(joinedload(models.Conversation.campaign))\
        .filter(models.Conversation.user_id == current_user.id)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                models.Conversation.phone_number.ilike(f"%{search}%"),
                models.Conversation.contact_name.ilike(f"%{search}%"),
                models.Conversation.transcript.ilike(f"%{search}%")
            )
        )
    
    if status_filter:
        query = query.filter(models.Conversation.status == status_filter)
    
    if campaign_filter:
        query = query.filter(models.Conversation.campaign_id == campaign_filter)
    
    # Date range filtering
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
    
    # Get total count for pagination
    total_conversations = query.count()
    
    # Get conversations with pagination
    conversations = query.order_by(desc(models.Conversation.created_at))\
        .offset(offset).limit(per_page).all()
    
    # Calculate pagination info
    total_pages = (total_conversations + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    # Get user campaigns for filter dropdown
    campaigns = db.query(models.Campaign)\
        .filter(models.Campaign.user_id == current_user.id)\
        .order_by(desc(models.Campaign.created_at))\
        .all()
    
    # Enhanced statistics
    stats = await get_enhanced_stats(current_user.id, db, query)
    
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "title": "Call History - TasKvox AI",
            "user": current_user,
            "conversations": conversations,
            "campaigns": campaigns,
            "pagination": {
                "page": page,
                "total_pages": total_pages,
                "has_prev": has_prev,
                "has_next": has_next,
                "total_items": total_conversations
            },
            "filters": {
                "search": search or "",
                "status_filter": status_filter or "",
                "campaign_filter": campaign_filter or "",
                "date_from": date_from or "",
                "date_to": date_to or ""
            },
            "stats": stats
        }
    )

async def get_enhanced_stats(user_id: int, db: Session, query):
    """Get enhanced statistics for history page"""
    
    # Basic stats from filtered query
    total_calls = query.count()
    completed_calls = query.filter(models.Conversation.status == "completed").count()
    failed_calls = query.filter(models.Conversation.status == "failed").count()
    in_progress_calls = query.filter(models.Conversation.status == "in_progress").count()
    
    # Duration statistics
    duration_result = query.filter(models.Conversation.duration_seconds.isnot(None))\
        .with_entities(
            func.sum(models.Conversation.duration_seconds).label('total'),
            func.avg(models.Conversation.duration_seconds).label('average'),
            func.max(models.Conversation.duration_seconds).label('longest'),
            func.min(models.Conversation.duration_seconds).label('shortest')
        ).first()
    
    # Call volume by hour (for the filtered dataset)
    hourly_volume = query.with_entities(
        func.extract('hour', models.Conversation.created_at).label('hour'),
        func.count(models.Conversation.id).label('count')
    ).group_by(func.extract('hour', models.Conversation.created_at)).all()
    
    return {
        "total_calls": total_calls,
        "completed_calls": completed_calls,
        "failed_calls": failed_calls,
        "in_progress_calls": in_progress_calls,
        "success_rate": (completed_calls / total_calls * 100) if total_calls > 0 else 0,
        "total_duration": duration_result.total or 0,
        "avg_duration": duration_result.average or 0,
        "longest_call": duration_result.longest or 0,
        "shortest_call": duration_result.shortest or 0,
        "hourly_volume": [{"hour": int(h.hour), "count": h.count} for h in hourly_volume]
    }

@router.get("/{conversation_id}")
async def get_conversation_details(
    conversation_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get detailed conversation information"""
    
    conversation = db.query(models.Conversation)\
        .options(joinedload(models.Conversation.agent))\
        .options(joinedload(models.Conversation.campaign))\
        .filter(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation": {
            "id": conversation.id,
            "phone_number": conversation.phone_number,
            "contact_name": conversation.contact_name,
            "status": conversation.status,
            "duration_seconds": conversation.duration_seconds,
            "transcript": conversation.transcript,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            "agent_name": conversation.agent.name if conversation.agent else "Unknown",
            "campaign_name": conversation.campaign.name if conversation.campaign else "Direct Call",
            "external_conversation_id": conversation.external_conversation_id,
            "cost": conversation.cost
        }
    }

# NEW: Download call recording as MP3
@router.get("/{conversation_id}/download-recording")
async def download_call_recording(
    conversation_id: int,
    format: str = Query("mp3", regex="^(mp3|wav)$"),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Download call recording in MP3 or WAV format"""
    
    conversation = db.query(models.Conversation)\
        .filter(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if not conversation.external_conversation_id:
        raise HTTPException(status_code=404, detail="No recording available")
    
    if not current_user.voice_api_key:
        raise HTTPException(status_code=400, detail="Voice AI API key not configured")
    
    try:
        # Get recording from ElevenLabs
        client = ElevenLabsClient(current_user.voice_api_key)
        audio_result = await client.get_conversation_audio(conversation.external_conversation_id)
        
        if not audio_result["success"]:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        audio_url = audio_result.get("audio_url")
        if not audio_url:
            raise HTTPException(status_code=404, detail="Recording URL not available")
        
        # Download audio file
        import httpx
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(audio_url)
            
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Failed to download recording")
            
            # Determine filename and content type
            contact_name = conversation.contact_name or "Unknown"
            safe_contact_name = "".join(c for c in contact_name if c.isalnum() or c in (' ', '-', '_')).strip()
            date_str = conversation.created_at.strftime("%Y%m%d_%H%M")
            filename = f"call_{safe_contact_name}_{date_str}.{format}"
            
            content_type = "audio/mpeg" if format == "mp3" else "audio/wav"
            
            return Response(
                content=response.content,
                media_type=content_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download recording: {str(e)}")

# NEW: Export transcript as PDF
@router.get("/{conversation_id}/download-transcript")
async def download_transcript(
    conversation_id: int,
    format: str = Query("pdf", regex="^(pdf|txt|json)$"),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Download conversation transcript in PDF, TXT, or JSON format"""
    
    conversation = db.query(models.Conversation)\
        .options(joinedload(models.Conversation.agent))\
        .options(joinedload(models.Conversation.campaign))\
        .filter(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if not conversation.transcript:
        raise HTTPException(status_code=404, detail="No transcript available")
    
    # Generate filename
    contact_name = conversation.contact_name or "Unknown"
    safe_contact_name = "".join(c for c in contact_name if c.isalnum() or c in (' ', '-', '_')).strip()
    date_str = conversation.created_at.strftime("%Y%m%d_%H%M")
    filename = f"transcript_{safe_contact_name}_{date_str}.{format}"
    
    if format == "txt":
        # Plain text format
        content = f"""TasKvox AI Call Transcript
===============================

Call Details:
- Contact: {conversation.contact_name or 'Unknown'}
- Phone: {conversation.phone_number}
- Date: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- Duration: {conversation.duration_seconds or 0} seconds
- Status: {conversation.status}
- Agent: {conversation.agent.name if conversation.agent else 'Unknown'}
- Campaign: {conversation.campaign.name if conversation.campaign else 'Direct Call'}

Transcript:
-----------
{conversation.transcript}

---
Generated by TasKvox AI on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return Response(
            content=content.encode('utf-8'),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    elif format == "json":
        # JSON format
        transcript_data = {
            "conversation_id": conversation.id,
            "contact_details": {
                "name": conversation.contact_name,
                "phone_number": conversation.phone_number
            },
            "call_details": {
                "date": conversation.created_at.isoformat(),
                "duration_seconds": conversation.duration_seconds,
                "status": conversation.status,
                "agent_name": conversation.agent.name if conversation.agent else None,
                "campaign_name": conversation.campaign.name if conversation.campaign else None
            },
            "transcript": conversation.transcript,
            "metadata": {
                "external_id": conversation.external_conversation_id,
                "cost": conversation.cost,
                "exported_at": datetime.now().isoformat()
            }
        }
        
        return Response(
            content=json.dumps(transcript_data, indent=2).encode('utf-8'),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    elif format == "pdf":
        # PDF format
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                doc = SimpleDocTemplate(tmp_file.name, pagesize=letter)
                story = []
                styles = getSampleStyleSheet()
                
                # Title
                title = Paragraph("TasKvox AI Call Transcript", styles['Title'])
                story.append(title)
                story.append(Spacer(1, 20))
                
                # Call details
                details = f"""
                <b>Contact:</b> {conversation.contact_name or 'Unknown'}<br/>
                <b>Phone:</b> {conversation.phone_number}<br/>
                <b>Date:</b> {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}<br/>
                <b>Duration:</b> {conversation.duration_seconds or 0} seconds<br/>
                <b>Status:</b> {conversation.status}<br/>
                <b>Agent:</b> {conversation.agent.name if conversation.agent else 'Unknown'}<br/>
                <b>Campaign:</b> {conversation.campaign.name if conversation.campaign else 'Direct Call'}
                """
                
                details_para = Paragraph(details, styles['Normal'])
                story.append(details_para)
                story.append(Spacer(1, 20))
                
                # Transcript header
                transcript_header = Paragraph("Transcript", styles['Heading2'])
                story.append(transcript_header)
                story.append(Spacer(1, 10))
                
                # Transcript content
                transcript_para = Paragraph(conversation.transcript.replace('\n', '<br/>'), styles['Normal'])
                story.append(transcript_para)
                
                doc.build(story)
                
                return FileResponse(
                    tmp_file.name,
                    media_type='application/pdf',
                    filename=filename
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Delete a conversation record"""
    
    conversation = db.query(models.Conversation)\
        .filter(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Update campaign statistics if this conversation was part of a campaign
    if conversation.campaign_id:
        campaign = db.query(models.Campaign)\
            .filter(models.Campaign.id == conversation.campaign_id).first()
        
        if campaign:
            campaign.completed_calls = max(0, campaign.completed_calls - 1)
            if conversation.status == "completed":
                campaign.successful_calls = max(0, campaign.successful_calls - 1)
            elif conversation.status == "failed":
                campaign.failed_calls = max(0, campaign.failed_calls - 1)
    
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversation deleted successfully"}