"""
TasKvox AI - Call History Router
View and manage conversation history
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, or_

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
    
    # Calculate total duration
    total_duration = db.query(models.Conversation)\
        .filter(
            models.Conversation.user_id == current_user.id,
            models.Conversation.duration_seconds.isnot(None)
        ).with_entities(
            db.func.sum(models.Conversation.duration_seconds)
        ).scalar() or 0
    
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
    
    # Try to get updated conversation data from ElevenLabs if we have the ID
    conversation_data = None
    if conversation.elevenlabs_conversation_id and current_user.elevenlabs_api_key:
        try:
            client = ElevenLabsClient(current_user.elevenlabs_api_key)
            result = await client.get_conversation(conversation.elevenlabs_conversation_id)
            if result["success"]:
                conversation_data = result["conversation"]
                
                # Update local conversation with fresh data
                if conversation_data.get("status"):
                    conversation.status = conversation_data["status"]
                if conversation_data.get("transcript"):
                    conversation.transcript = conversation_data["transcript"]
                if conversation_data.get("duration_seconds"):
                    conversation.duration_seconds = conversation_data["duration_seconds"]
                
                db.commit()
        except Exception as e:
            print(f"Error fetching conversation from ElevenLabs: {e}")
    
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
        },
        "elevenlabs_data": conversation_data
    }

@router.get("/{conversation_id}/audio")
async def get_conversation_audio(
    conversation_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get conversation audio URL"""
    
    conversation = db.query(models.Conversation)\
        .filter(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if not conversation.elevenlabs_conversation_id:
        raise HTTPException(status_code=404, detail="Audio not available")
    
    if not current_user.elevenlabs_api_key:
        raise HTTPException(status_code=400, detail="API key not configured")
    
    try:
        client = ElevenLabsClient(current_user.elevenlabs_api_key)
        result = await client.get_conversation_audio(conversation.elevenlabs_conversation_id)
        
        if result["success"]:
            return result["audio"]
        else:
            raise HTTPException(status_code=404, detail="Audio not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving audio: {str(e)}")

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

@router.post("/export")
async def export_conversations(
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    campaign_filter: Optional[int] = None,
    format: str = "csv",
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Export conversation history"""
    
    # Build query with same filters as history page
    query = db.query(models.Conversation)\
        .options(joinedload(models.Conversation.agent))\
        .options(joinedload(models.Conversation.campaign))\
        .filter(models.Conversation.user_id == current_user.id)
    
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
    
    conversations = query.order_by(desc(models.Conversation.created_at)).all()
    
    # Prepare export data
    export_data = []
    for conv in conversations:
        export_data.append({
            "id": conv.id,
            "phone_number": conv.phone_number,
            "contact_name": conv.contact_name or "",
            "agent_name": conv.agent.name if conv.agent else "",
            "campaign_name": conv.campaign.name if conv.campaign else "Direct Call",
            "status": conv.status or "",
            "duration_seconds": conv.duration_seconds or 0,
            "transcript": conv.transcript or "",
            "created_at": conv.created_at.isoformat(),
        })
    
    if format.lower() == "json":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=export_data,
            headers={"Content-Disposition": "attachment; filename=conversations.json"}
        )
    else:
        # CSV export
        import csv
        from fastapi.responses import StreamingResponse
        import io
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "phone_number", "contact_name", "agent_name", 
            "campaign_name", "status", "duration_seconds", "transcript", "created_at"
        ])
        writer.writeheader()
        writer.writerows(export_data)
        
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=conversations.csv"}
        )

@router.get("/stats/summary")
async def get_history_stats(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get detailed history statistics"""
    
    from datetime import datetime, timedelta
    from sqlalchemy import func, case
    
    # Date ranges
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Overall stats
    total_conversations = db.query(models.Conversation)\
        .filter(models.Conversation.user_id == current_user.id).count()
    
    # Status breakdown
    status_stats = db.query(
        models.Conversation.status,
        func.count(models.Conversation.id).label('count')
    ).filter(models.Conversation.user_id == current_user.id)\
     .group_by(models.Conversation.status).all()
    
    # Daily stats for the last 30 days
    daily_stats = db.query(
        func.date(models.Conversation.created_at).label('date'),
        func.count(models.Conversation.id).label('total_calls'),
        func.sum(
            case(
                (models.Conversation.status == 'completed', 1),
                else_=0
            )
        ).label('successful_calls')
    ).filter(
        and_(
            models.Conversation.user_id == current_user.id,
            models.Conversation.created_at >= month_ago
        )
    ).group_by(func.date(models.Conversation.created_at))\
     .order_by(func.date(models.Conversation.created_at)).all()
    
    # Average call duration
    avg_duration = db.query(func.avg(models.Conversation.duration_seconds))\
        .filter(
            and_(
                models.Conversation.user_id == current_user.id,
                models.Conversation.duration_seconds.isnot(None),
                models.Conversation.status == 'completed'
            )
        ).scalar() or 0
    
    return {
        "total_conversations": total_conversations,
        "status_breakdown": [
            {"status": status, "count": count}
            for status, count in status_stats
        ],
        "daily_stats": [
            {
                "date": stat.date.isoformat(),
                "total_calls": stat.total_calls,
                "successful_calls": stat.successful_calls,
                "success_rate": (stat.successful_calls / stat.total_calls * 100) if stat.total_calls > 0 else 0
            }
            for stat in daily_stats
        ],
        "average_duration": round(avg_duration, 2) if avg_duration else 0
    }