"""
TasKvox AI - Complete Reports Router with 100% Real Data
No mock data - everything calculated from actual database
FILE: app/routers/reports.py - REPLACE ENTIRE FILE
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Query, Response
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, extract, text
from datetime import datetime, timedelta, date
import json
import csv
import io
import tempfile
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from app.database import get_db
from app import models, auth

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
async def reports_dashboard(
    request: Request,
    date_range: str = Query("30", description="Days to analyze"),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Advanced reports and analytics dashboard - 100% REAL DATA"""
    
    # Calculate date range
    days = int(date_range) if date_range.isdigit() else 30
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get comprehensive statistics
    stats = await get_comprehensive_stats(current_user.id, db, start_date, end_date)
    
    # Get chart data
    daily_stats = await get_daily_call_stats(current_user.id, db, start_date, end_date)
    agent_performance = await get_agent_performance(current_user.id, db, start_date, end_date)
    campaign_analysis = await get_campaign_analysis(current_user.id, db, start_date, end_date)
    hourly_distribution = await get_hourly_call_distribution(current_user.id, db, start_date, end_date)
    duration_distribution = await get_duration_distribution(current_user.id, db, start_date, end_date)
    weekly_distribution = await get_weekly_distribution(current_user.id, db, start_date, end_date)
    
    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "title": "Reports & Analytics - TasKvox AI",
            "user": current_user,
            "stats": stats,
            "daily_stats": daily_stats,
            "agent_performance": agent_performance,
            "campaign_analysis": campaign_analysis,
            "hourly_distribution": hourly_distribution,
            "duration_distribution": duration_distribution,
            "weekly_distribution": weekly_distribution,
            "date_range": days,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        }
    )

async def get_comprehensive_stats(user_id: int, db: Session, start_date: datetime, end_date: datetime):
    """Get comprehensive statistics - 100% REAL DATA"""
    
    # Base query for the date range
    base_query = db.query(models.Conversation).filter(
        and_(
            models.Conversation.user_id == user_id,
            models.Conversation.created_at.between(start_date, end_date)
        )
    )
    
    # Basic counts - REAL DATA
    total_calls = base_query.count()
    completed_calls = base_query.filter(models.Conversation.status == "completed").count()
    failed_calls = base_query.filter(models.Conversation.status == "failed").count()
    in_progress_calls = base_query.filter(models.Conversation.status == "in_progress").count()
    
    # Duration statistics - REAL DATA
    duration_stats = base_query.filter(models.Conversation.duration_seconds.isnot(None))\
        .with_entities(
            func.avg(models.Conversation.duration_seconds).label('avg_duration'),
            func.sum(models.Conversation.duration_seconds).label('total_duration'),
            func.max(models.Conversation.duration_seconds).label('max_duration'),
            func.min(models.Conversation.duration_seconds).label('min_duration')
        ).first()
    
    # Success rate calculation - REAL DATA
    success_rate = (completed_calls / total_calls * 100) if total_calls > 0 else 0
    
    # Campaign statistics - REAL DATA
    total_campaigns = db.query(models.Campaign).filter(
        and_(
            models.Campaign.user_id == user_id,
            models.Campaign.created_at.between(start_date, end_date)
        )
    ).count()
    
    # Agent statistics - REAL DATA
    active_agents = db.query(models.Agent).filter(
        and_(
            models.Agent.user_id == user_id,
            models.Agent.is_active == True
        )
    ).count()
    
    # Peak call day - REAL DATA
    peak_day_result = base_query.with_entities(
        func.date(models.Conversation.created_at).label('call_date'),
        func.count(models.Conversation.id).label('call_count')
    ).group_by(func.date(models.Conversation.created_at))\
     .order_by(func.count(models.Conversation.id).desc()).first()
    
    return {
        "total_calls": total_calls,
        "completed_calls": completed_calls,
        "failed_calls": failed_calls,
        "in_progress_calls": in_progress_calls,
        "success_rate": round(success_rate, 2),
        "total_campaigns": total_campaigns,
        "active_agents": active_agents,
        "avg_duration": round(duration_stats.avg_duration or 0, 2),
        "total_duration": duration_stats.total_duration or 0,
        "max_duration": duration_stats.max_duration or 0,
        "min_duration": duration_stats.min_duration or 0,
        "peak_day": {
            "date": peak_day_result.call_date.strftime('%Y-%m-%d') if peak_day_result else "N/A",
            "calls": peak_day_result.call_count if peak_day_result else 0
        }
    }

async def get_daily_call_stats(user_id: int, db: Session, start_date: datetime, end_date: datetime):
    """Get daily call statistics - 100% REAL DATA"""
    
    # Get all calls per day - REAL DATA
    daily_data = db.query(
        func.date(models.Conversation.created_at).label('call_date'),
        func.count(models.Conversation.id).label('total_calls')
    ).filter(
        and_(
            models.Conversation.user_id == user_id,
            models.Conversation.created_at.between(start_date, end_date)
        )
    ).group_by(func.date(models.Conversation.created_at))\
     .order_by(func.date(models.Conversation.created_at)).all()
    
    # Get successful calls per day - REAL DATA
    successful_data = db.query(
        func.date(models.Conversation.created_at).label('call_date'),
        func.count(models.Conversation.id).label('successful_calls')
    ).filter(
        and_(
            models.Conversation.user_id == user_id,
            models.Conversation.created_at.between(start_date, end_date),
            models.Conversation.status == 'completed'
        )
    ).group_by(func.date(models.Conversation.created_at)).all()
    
    # Get failed calls per day - REAL DATA
    failed_data = db.query(
        func.date(models.Conversation.created_at).label('call_date'),
        func.count(models.Conversation.id).label('failed_calls')
    ).filter(
        and_(
            models.Conversation.user_id == user_id,
            models.Conversation.created_at.between(start_date, end_date),
            models.Conversation.status == 'failed'
        )
    ).group_by(func.date(models.Conversation.created_at)).all()
    
    # Get average duration per day - REAL DATA
    duration_data = db.query(
        func.date(models.Conversation.created_at).label('call_date'),
        func.avg(models.Conversation.duration_seconds).label('avg_duration')
    ).filter(
        and_(
            models.Conversation.user_id == user_id,
            models.Conversation.created_at.between(start_date, end_date),
            models.Conversation.duration_seconds.isnot(None)
        )
    ).group_by(func.date(models.Conversation.created_at)).all()
    
    # Create lookups for easy access
    successful_lookup = {str(s.call_date): s.successful_calls for s in successful_data}
    failed_lookup = {str(f.call_date): f.failed_calls for f in failed_data}
    duration_lookup = {str(d.call_date): d.avg_duration for d in duration_data}
    
    return [
        {
            "date": stat.call_date.strftime('%Y-%m-%d'),
            "total_calls": stat.total_calls,
            "successful_calls": successful_lookup.get(str(stat.call_date), 0),
            "failed_calls": failed_lookup.get(str(stat.call_date), 0),
            "success_rate": (successful_lookup.get(str(stat.call_date), 0) / stat.total_calls * 100) if stat.total_calls > 0 else 0,
            "avg_duration": round(duration_lookup.get(str(stat.call_date), 0) or 0, 2)
        }
        for stat in daily_data
    ]

async def get_agent_performance(user_id: int, db: Session, start_date: datetime, end_date: datetime):
    """Get agent performance - 100% REAL DATA"""
    
    # Get total calls per agent - REAL DATA
    agent_stats = db.query(
        models.Agent.name.label('agent_name'),
        models.Agent.id.label('agent_id'),
        func.count(models.Conversation.id).label('total_calls')
    ).join(models.Conversation, models.Agent.id == models.Conversation.agent_id)\
     .filter(
         and_(
             models.Agent.user_id == user_id,
             models.Conversation.created_at.between(start_date, end_date)
         )
     ).group_by(models.Agent.id, models.Agent.name)\
      .order_by(func.count(models.Conversation.id).desc()).all()
    
    # Get successful calls per agent - REAL DATA
    successful_stats = db.query(
        models.Agent.id.label('agent_id'),
        func.count(models.Conversation.id).label('successful_calls')
    ).join(models.Conversation, models.Agent.id == models.Conversation.agent_id)\
     .filter(
         and_(
             models.Agent.user_id == user_id,
             models.Conversation.created_at.between(start_date, end_date),
             models.Conversation.status == 'completed'
         )
     ).group_by(models.Agent.id).all()
    
    # Get average duration per agent - REAL DATA
    duration_stats = db.query(
        models.Agent.id.label('agent_id'),
        func.avg(models.Conversation.duration_seconds).label('avg_duration')
    ).join(models.Conversation, models.Agent.id == models.Conversation.agent_id)\
     .filter(
         and_(
             models.Agent.user_id == user_id,
             models.Conversation.created_at.between(start_date, end_date),
             models.Conversation.duration_seconds.isnot(None)
         )
     ).group_by(models.Agent.id).all()
    
    # Create lookups
    successful_lookup = {s.agent_id: s.successful_calls for s in successful_stats}
    duration_lookup = {d.agent_id: d.avg_duration for d in duration_stats}
    
    return [
        {
            "agent_id": stat.agent_id,
            "agent_name": stat.agent_name,
            "total_calls": stat.total_calls,
            "successful_calls": successful_lookup.get(stat.agent_id, 0),
            "success_rate": (successful_lookup.get(stat.agent_id, 0) / stat.total_calls * 100) if stat.total_calls > 0 else 0,
            "avg_duration": round(duration_lookup.get(stat.agent_id, 0) or 0, 2)
        }
        for stat in agent_stats
    ]

async def get_campaign_analysis(user_id: int, db: Session, start_date: datetime, end_date: datetime):
    """Get campaign analysis - 100% REAL DATA"""
    
    campaign_stats = db.query(
        models.Campaign.name.label('campaign_name'),
        models.Campaign.id.label('campaign_id'),
        models.Campaign.status.label('campaign_status'),
        models.Campaign.total_contacts,
        models.Campaign.completed_calls,
        models.Campaign.successful_calls,
        models.Campaign.failed_calls
    ).filter(
        and_(
            models.Campaign.user_id == user_id,
            models.Campaign.created_at.between(start_date, end_date)
        )
    ).order_by(models.Campaign.created_at.desc()).all()
    
    return [
        {
            "campaign_id": stat.campaign_id,
            "campaign_name": stat.campaign_name,
            "status": stat.campaign_status,
            "total_contacts": stat.total_contacts or 0,
            "completed_calls": stat.completed_calls or 0,
            "successful_calls": stat.successful_calls or 0,
            "failed_calls": stat.failed_calls or 0,
            "completion_rate": (stat.completed_calls / stat.total_contacts * 100) if stat.total_contacts and stat.total_contacts > 0 else 0,
            "success_rate": (stat.successful_calls / stat.completed_calls * 100) if stat.completed_calls and stat.completed_calls > 0 else 0
        }
        for stat in campaign_stats
    ]

async def get_hourly_call_distribution(user_id: int, db: Session, start_date: datetime, end_date: datetime):
    """Get hourly call distribution - 100% REAL DATA"""
    
    hourly_stats = db.query(
        extract('hour', models.Conversation.created_at).label('hour'),
        func.count(models.Conversation.id).label('call_count')
    ).filter(
        and_(
            models.Conversation.user_id == user_id,
            models.Conversation.created_at.between(start_date, end_date)
        )
    ).group_by(extract('hour', models.Conversation.created_at))\
     .order_by(extract('hour', models.Conversation.created_at)).all()
    
    # Create 24-hour distribution with REAL DATA
    hourly_distribution = [{"hour": i, "call_count": 0} for i in range(24)]
    
    for stat in hourly_stats:
        hour_index = int(stat.hour)
        if 0 <= hour_index < 24:
            hourly_distribution[hour_index] = {
                "hour": hour_index,
                "call_count": stat.call_count
            }
    
    return hourly_distribution

async def get_duration_distribution(user_id: int, db: Session, start_date: datetime, end_date: datetime):
    """Get call duration distribution - 100% REAL DATA"""
    
    # Get all durations for the period
    durations = db.query(models.Conversation.duration_seconds)\
        .filter(
            and_(
                models.Conversation.user_id == user_id,
                models.Conversation.created_at.between(start_date, end_date),
                models.Conversation.duration_seconds.isnot(None)
            )
        ).all()
    
    # Categorize durations into ranges - REAL DATA
    ranges = {
        "0-30s": 0,
        "30s-1m": 0, 
        "1-3m": 0,
        "3-5m": 0,
        "5m+": 0
    }
    
    for duration_row in durations:
        duration = duration_row[0] if duration_row[0] else 0
        
        if duration <= 30:
            ranges["0-30s"] += 1
        elif duration <= 60:
            ranges["30s-1m"] += 1
        elif duration <= 180:
            ranges["1-3m"] += 1
        elif duration <= 300:
            ranges["3-5m"] += 1
        else:
            ranges["5m+"] += 1
    
    return [
        {"range": range_name, "count": count}
        for range_name, count in ranges.items()
    ]

async def get_weekly_distribution(user_id: int, db: Session, start_date: datetime, end_date: datetime):
    """Get weekly call distribution - 100% REAL DATA"""
    
    # Get calls by day of week (0=Monday, 6=Sunday)
    weekly_stats = db.query(
        extract('dow', models.Conversation.created_at).label('day_of_week'),
        func.count(models.Conversation.id).label('call_count')
    ).filter(
        and_(
            models.Conversation.user_id == user_id,
            models.Conversation.created_at.between(start_date, end_date)
        )
    ).group_by(extract('dow', models.Conversation.created_at)).all()
    
    # Create weekly distribution (Monday=0, Sunday=6)
    week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekly_distribution = [{"day": day, "call_count": 0} for day in week_days]
    
    # PostgreSQL: Sunday=0, Monday=1, ... Saturday=6
    # We want: Monday=0, Tuesday=1, ... Sunday=6
    for stat in weekly_stats:
        pg_dow = int(stat.day_of_week)  # PostgreSQL day of week
        # Convert PostgreSQL DOW to our format
        our_dow = (pg_dow + 6) % 7  # Sunday(0) becomes 6, Monday(1) becomes 0
        if 0 <= our_dow < 7:
            weekly_distribution[our_dow] = {
                "day": week_days[our_dow],
                "call_count": stat.call_count
            }
    
    return weekly_distribution

@router.get("/export/pdf")
async def export_report_pdf(
    date_range: str = Query("30"),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Export comprehensive report as PDF - 100% REAL DATA"""
    
    # Calculate date range
    days = int(date_range) if date_range.isdigit() else 30
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get REAL data
    stats = await get_comprehensive_stats(current_user.id, db, start_date, end_date)
    agent_performance = await get_agent_performance(current_user.id, db, start_date, end_date)
    
    # Create PDF with REAL data
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        doc = SimpleDocTemplate(tmp_file.name, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("TasKvox AI - Analytics Report", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Report period
        period = Paragraph(f"Report Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", styles['Normal'])
        story.append(period)
        story.append(Spacer(1, 20))
        
        # Summary statistics - ALL REAL DATA
        summary = Paragraph("Summary Statistics", styles['Heading2'])
        story.append(summary)
        
        summary_data = [
            ["Metric", "Value"],
            ["Total Calls", str(stats['total_calls'])],
            ["Successful Calls", str(stats['completed_calls'])],
            ["Failed Calls", str(stats['failed_calls'])],
            ["Success Rate", f"{stats['success_rate']}%"],
            ["Average Duration", f"{stats['avg_duration']} seconds"],
            ["Total Talk Time", f"{stats['total_duration']} seconds"],
            ["Active Agents", str(stats['active_agents'])],
            ["Total Campaigns", str(stats['total_campaigns'])]
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 30))
        
        # Agent performance - ALL REAL DATA
        if agent_performance:
            agent_heading = Paragraph("Agent Performance", styles['Heading2'])
            story.append(agent_heading)
            
            agent_data = [["Agent Name", "Total Calls", "Success Rate", "Avg Duration"]]
            for agent in agent_performance:
                agent_data.append([
                    agent['agent_name'],
                    str(agent['total_calls']),
                    f"{agent['success_rate']:.1f}%",
                    f"{agent['avg_duration']:.1f}s"
                ])
            
            agent_table = Table(agent_data)
            agent_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(agent_table)
        
        doc.build(story)
        
        return FileResponse(
            tmp_file.name,
            media_type='application/pdf',
            filename=f'taskvox_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf'
        )

@router.get("/api/chart-data")
async def get_chart_data(
    chart_type: str = Query(..., description="Chart type: daily, agent, campaign, hourly, duration, weekly"),
    date_range: str = Query("30"),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get specific chart data via API - 100% REAL DATA"""
    
    days = int(date_range) if date_range.isdigit() else 30
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    if chart_type == "daily":
        return await get_daily_call_stats(current_user.id, db, start_date, end_date)
    elif chart_type == "agent":
        return await get_agent_performance(current_user.id, db, start_date, end_date)
    elif chart_type == "campaign":
        return await get_campaign_analysis(current_user.id, db, start_date, end_date)
    elif chart_type == "hourly":
        return await get_hourly_call_distribution(current_user.id, db, start_date, end_date)
    elif chart_type == "duration":
        return await get_duration_distribution(current_user.id, db, start_date, end_date)
    elif chart_type == "weekly":
        return await get_weekly_distribution(current_user.id, db, start_date, end_date)
    else:
        raise HTTPException(status_code=400, detail="Invalid chart type")