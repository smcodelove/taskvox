"""
TasKvox AI - Fixed Dashboard Router
Replace your app/routers/dashboard.py with this
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from datetime import datetime, timedelta

from app.database import get_db
from app import models, schemas, auth

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Dashboard page"""
    # Get dashboard statistics
    stats = await get_dashboard_stats(current_user.id, db)
    
    # Get recent activity
    recent_conversations = db.query(models.Conversation)\
        .filter(models.Conversation.user_id == current_user.id)\
        .order_by(models.Conversation.created_at.desc())\
        .limit(5).all()
    
    recent_campaigns = db.query(models.Campaign)\
        .filter(models.Campaign.user_id == current_user.id)\
        .order_by(models.Campaign.created_at.desc())\
        .limit(5).all()
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "Dashboard - TasKvox AI",
            "user": current_user,
            "stats": stats,
            "recent_conversations": recent_conversations,
            "recent_campaigns": recent_campaigns
        }
    )

@router.get("/api/dashboard/stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats_api(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics via API"""
    return await get_dashboard_stats(current_user.id, db)

async def get_dashboard_stats(user_id: int, db: Session) -> schemas.DashboardStats:
    """Calculate dashboard statistics"""
    
    # Count totals
    total_agents = db.query(models.Agent)\
        .filter(and_(models.Agent.user_id == user_id, models.Agent.is_active == True))\
        .count()
    
    total_campaigns = db.query(models.Campaign)\
        .filter(models.Campaign.user_id == user_id)\
        .count()
    
    total_conversations = db.query(models.Conversation)\
        .filter(models.Conversation.user_id == user_id)\
        .count()
    
    active_campaigns = db.query(models.Campaign)\
        .filter(and_(
            models.Campaign.user_id == user_id,
            models.Campaign.status.in_(["pending", "running"])
        )).count()
    
    # Calculate success rate
    successful_calls = db.query(models.Conversation)\
        .filter(and_(
            models.Conversation.user_id == user_id,
            models.Conversation.status == "completed"
        )).count()
    
    success_rate = 0.0
    if total_conversations > 0:
        success_rate = (successful_calls / total_conversations) * 100
    
    # Calculate total cost (simplified for now)
    total_cost = "$0.00"
    
    return schemas.DashboardStats(
        total_agents=total_agents,
        total_campaigns=total_campaigns,
        total_conversations=total_conversations,
        active_campaigns=active_campaigns,
        success_rate=round(success_rate, 2),
        total_cost=total_cost
    )

@router.get("/api/dashboard/recent-activity")
async def get_recent_activity(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get recent activity"""
    recent_conversations = db.query(models.Conversation)\
        .filter(models.Conversation.user_id == current_user.id)\
        .order_by(models.Conversation.created_at.desc())\
        .limit(10).all()
    
    recent_campaigns = db.query(models.Campaign)\
        .filter(models.Campaign.user_id == current_user.id)\
        .order_by(models.Campaign.created_at.desc())\
        .limit(10).all()
    
    return {
        "conversations": [
            {
                "id": conv.id,
                "phone_number": conv.phone_number,
                "status": conv.status,
                "duration": conv.duration_seconds,
                "created_at": conv.created_at.isoformat()
            }
            for conv in recent_conversations
        ],
        "campaigns": [
            {
                "id": camp.id,
                "name": camp.name,
                "status": camp.status,
                "completed_calls": camp.completed_calls,
                "total_contacts": camp.total_contacts,
                "created_at": camp.created_at.isoformat()
            }
            for camp in recent_campaigns
        ]
    }

@router.get("/api/dashboard/charts")
async def get_dashboard_charts(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get chart data for dashboard"""
    
    # Campaign status distribution
    campaign_status = db.query(
        models.Campaign.status,
        func.count(models.Campaign.id).label('count')
    ).filter(models.Campaign.user_id == current_user.id)\
     .group_by(models.Campaign.status).all()
    
    # Call success rate over time (last 30 days) - simplified version
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Simplified daily stats without case statement
    daily_stats = db.query(
        func.date(models.Conversation.created_at).label('date'),
        func.count(models.Conversation.id).label('total_calls')
    ).filter(and_(
        models.Conversation.user_id == current_user.id,
        models.Conversation.created_at >= thirty_days_ago
    )).group_by(func.date(models.Conversation.created_at))\
     .order_by(func.date(models.Conversation.created_at)).all()
    
    # Calculate successful calls separately
    successful_stats = db.query(
        func.date(models.Conversation.created_at).label('date'),
        func.count(models.Conversation.id).label('successful_calls')
    ).filter(and_(
        models.Conversation.user_id == current_user.id,
        models.Conversation.created_at >= thirty_days_ago,
        models.Conversation.status == 'completed'
    )).group_by(func.date(models.Conversation.created_at))\
     .order_by(func.date(models.Conversation.created_at)).all()
    
    # Combine results
    successful_dict = {str(stat.date): stat.successful_calls for stat in successful_stats}
    
    return {
        "campaign_status": [
            {"status": status, "count": count}
            for status, count in campaign_status
        ],
        "daily_stats": [
            {
                "date": str(stat.date),
                "total_calls": stat.total_calls,
                "successful_calls": successful_dict.get(str(stat.date), 0),
                "success_rate": (successful_dict.get(str(stat.date), 0) / stat.total_calls * 100) if stat.total_calls > 0 else 0
            }
            for stat in daily_stats
        ]
    }