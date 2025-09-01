"""
TasKvox AI - Fixed History Router
Replace your app/routers/history.py - fix db.func issue
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, or_, func
from datetime import datetime, timedelta

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
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Call history page with pagination and filters"""
    
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
    
    # Get summary statistics
    total_calls = db.query(models.Conversation)\
        .filter(models.Conversation.user_id == current_user.id).count()
    
    successful_calls = db.query(models.Conversation)\
        .filter(
            models.Conversation.user_id == current_user.id,
            models.Conversation.status == "completed"
        ).count()
    
    failed_calls = db.query(models.Conversation)\
        .filter(
            models.Conversation.user_id == current_user.id,
            models.Conversation.status == "failed"
        ).count()
    
    # Calculate total duration - FIXED: use func from sqlalchemy
    total_duration_result = db.query(func.sum(models.Conversation.duration_seconds))\
        .filter(
            models.Conversation.user_id == current_user.id,
            models.Conversation.duration_seconds.isnot(None)
        ).scalar()
    
    total_duration = total_duration_result or 0
    
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
                "campaign_filter": campaign_filter or ""
            },
            "stats": {
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "total_duration": total_duration,
                "avg_duration": (total_duration / successful_calls) if successful_calls > 0 else 0
            }
        }
    )

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
            "agent_name": conversation.agent.name if conversation.agent else "Unknown",
            "campaign_name": conversation.campaign.name if conversation.campaign else "Direct Call",
            "elevenlabs_conversation_id": conversation.elevenlabs_conversation_id
        }
    }

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