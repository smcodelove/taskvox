# FILE: app/routers/campaigns.py
# REPLACE YOUR ENTIRE app/routers/campaigns.py WITH THIS

"""
TasKvox AI - Campaigns Router (Enhanced with Single Call Feature)
No ElevenLabs references visible to client
"""
import io
import csv
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from datetime import datetime
from ..plivo_client import PlivoClient 

from app.database import get_db
from app import models, schemas, auth
from app.elevenlabs_client import ElevenLabsClient

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# NEW: Pydantic models for single call
class SingleCallRequest(BaseModel):
    agent_id: int
    phone_number: str
    contact_name: Optional[str] = None
    call_purpose: Optional[str] = "test"
    notes: Optional[str] = None

@router.get("", response_class=HTMLResponse)
async def campaigns_page(
    request: Request,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Voice campaigns management page (white-label)"""
    campaigns = db.query(models.Campaign)\
        .filter(models.Campaign.user_id == current_user.id)\
        .order_by(models.Campaign.created_at.desc()).all()
    
    agents = db.query(models.Agent)\
        .filter(models.Agent.user_id == current_user.id, models.Agent.is_active == True)\
        .all()
    
    return templates.TemplateResponse(
        "campaigns.html",
        {
            "request": request,
            "title": "Voice Campaigns - TasKvox AI",
            "user": current_user,
            "campaigns": campaigns,
            "agents": agents
        }
    )

@router.post("")
async def create_campaign_form(
    request: Request,
    name: str = Form(...),
    agent_id: int = Form(...),
    csv_file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Create voice campaign from form submission (white-label)"""
    try:
        # Validate CSV file
        if not csv_file.filename.endswith('.csv'):
            return RedirectResponse(url="/campaigns?error=File must be CSV", status_code=302)
        
        # Verify agent exists
        agent = db.query(models.Agent)\
            .filter(models.Agent.id == agent_id, models.Agent.user_id == current_user.id)\
            .first()
        
        if not agent:
            return RedirectResponse(url="/campaigns?error=Voice agent not found", status_code=302)
        
        # Read and parse CSV
        content = await csv_file.read()
        csv_content = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        # Validate required columns
        fieldnames = csv_reader.fieldnames or []
        if 'phone_number' not in fieldnames:
            return RedirectResponse(url="/campaigns?error=CSV must contain phone_number column", status_code=302)
        
        # Create campaign
        campaign = models.Campaign(
            user_id=current_user.id,
            agent_id=agent_id,
            name=name,
            status="pending"
        )
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        # Process contacts and create conversations
        contacts_processed = 0
        
        for row in csv_reader:
            phone_number = str(row.get('phone_number', '')).strip()
            contact_name = str(row.get('name', '')).strip() if 'name' in row else None
            
            if phone_number and phone_number != 'nan':
                conversation = models.Conversation(
                    user_id=current_user.id,
                    agent_id=agent_id,
                    campaign_id=campaign.id,
                    phone_number=phone_number,
                    contact_name=contact_name if contact_name else None,
                    status="pending"
                )
                db.add(conversation)
                contacts_processed += 1
        
        # Update campaign with contact count
        campaign.total_contacts = contacts_processed
        db.commit()
        
        return RedirectResponse(url=f"/campaigns?success=Voice campaign created with {contacts_processed} contacts", status_code=302)
        
    except Exception as e:
        return RedirectResponse(url=f"/campaigns?error=Error creating voice campaign: {str(e)}", status_code=302)

# NEW: Single Call API Endpoint
@router.post("/api/single-call")
async def make_single_call(
    call_request: SingleCallRequest,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Make a single outbound call"""
    try:
        # Get the agent
        agent = db.query(models.Agent)\
            .filter(models.Agent.id == call_request.agent_id, models.Agent.user_id == current_user.id)\
            .first()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if not agent.external_agent_id:
            raise HTTPException(status_code=400, detail="Agent not connected to Voice AI service")
        
        if not current_user.voice_api_key:
            raise HTTPException(status_code=400, detail="Voice AI API key not configured")
        
        # Create conversation record
        conversation = models.Conversation(
            user_id=current_user.id,
            agent_id=agent.id,
            phone_number=call_request.phone_number,
            contact_name=call_request.contact_name,
            status="initiating"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        # Make the call using ElevenLabs
        client = ElevenLabsClient(current_user.voice_api_key)
        
        # Create metadata for the call
        call_metadata = {
            "contact_name": call_request.contact_name,
            "call_purpose": call_request.call_purpose,
            "notes": call_request.notes,
            "conversation_id": conversation.id,
            "call_type": "single_call"
        }
        
        result = await client.make_single_call(
            agent.external_agent_id,
            call_request.phone_number,
            metadata=call_metadata
        )
        
        if result["success"]:
            # Update conversation with external ID
            conversation.external_conversation_id = result["call"].get("conversation_id")
            conversation.status = "in_progress"
            db.commit()
            
            return {
                "success": True,
                "message": "Call initiated successfully",
                "conversation_id": conversation.id,
                "status": "in_progress",
                "phone_number": call_request.phone_number,
                "contact_name": call_request.contact_name,
                "agent_name": agent.name
            }
        else:
            # Update status to failed
            conversation.status = "failed"
            db.commit()
            
            raise HTTPException(
                status_code=400,
                detail=f"Failed to initiate call: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        # Update conversation status if exists
        if 'conversation' in locals():
            conversation.status = "failed"
            db.commit()
        
        raise HTTPException(status_code=500, detail=f"Call initiation error: {str(e)}")

# NEW: Get Recent Single Calls
@router.get("/api/recent-single-calls")
async def get_recent_single_calls(
    limit: int = 10,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get recent single calls (calls without campaign_id)"""
    recent_calls = db.query(models.Conversation)\
        .filter(
            models.Conversation.user_id == current_user.id,
            models.Conversation.campaign_id.is_(None)  # Single calls have no campaign
        )\
        .order_by(desc(models.Conversation.created_at))\
        .limit(limit).all()
    
    return {
        "calls": [
            {
                "id": call.id,
                "phone_number": call.phone_number,
                "contact_name": call.contact_name,
                "status": call.status,
                "duration_seconds": call.duration_seconds,
                "created_at": call.created_at.isoformat(),
                "agent_id": call.agent_id
            }
            for call in recent_calls
        ],
        "total": len(recent_calls)
    }

# NEW: Single Call Statistics
@router.get("/api/single-call-stats")
async def get_single_call_statistics(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get statistics for single calls"""
    from sqlalchemy import func
    
    # Get single calls (no campaign_id)
    single_calls_query = db.query(models.Conversation)\
        .filter(
            models.Conversation.user_id == current_user.id,
            models.Conversation.campaign_id.is_(None)
        )
    
    total_single_calls = single_calls_query.count()
    
    completed_single_calls = single_calls_query\
        .filter(models.Conversation.status == "completed").count()
    
    failed_single_calls = single_calls_query\
        .filter(models.Conversation.status == "failed").count()
    
    # Average duration for single calls
    avg_duration = single_calls_query\
        .filter(models.Conversation.duration_seconds.isnot(None))\
        .with_entities(func.avg(models.Conversation.duration_seconds))\
        .scalar() or 0
    
    success_rate = (completed_single_calls / total_single_calls * 100) if total_single_calls > 0 else 0
    
    return {
        "total_single_calls": total_single_calls,
        "completed_calls": completed_single_calls,
        "failed_calls": failed_single_calls,
        "success_rate": round(success_rate, 2),
        "average_duration": round(avg_duration, 2)
    }

@router.post("/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Launch voice campaign (white-label)"""
    campaign = db.query(models.Campaign)\
        .filter(models.Campaign.id == campaign_id, models.Campaign.user_id == current_user.id)\
        .first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Voice campaign not found")
    
    if campaign.status != "pending":
        raise HTTPException(status_code=400, detail="Campaign can only be launched from pending status")
    
    # Check API key
    if not current_user.voice_api_key:
        raise HTTPException(status_code=400, detail="Voice AI API key not configured")
    
    # Get agent
    agent = db.query(models.Agent).filter(models.Agent.id == campaign.agent_id).first()
    if not agent or not agent.external_agent_id:
        raise HTTPException(status_code=400, detail="Voice agent not found or not linked to Voice AI service")
    
    # Get pending conversations
    conversations = db.query(models.Conversation)\
        .filter(models.Conversation.campaign_id == campaign_id, models.Conversation.status == "pending")\
        .limit(5).all()  # Limit to 5 calls for testing
    
    if not conversations:
        raise HTTPException(status_code=400, detail="No contacts to call")
    
    # Update campaign status
    campaign.status = "running"
    db.commit()
    
    # Make calls using Voice AI
    client = ElevenLabsClient(current_user.voice_api_key)
    successful_calls = 0
    failed_calls = 0
    
    for conversation in conversations:
        try:
            result = await client.make_single_call(
                agent.external_agent_id,
                conversation.phone_number,
                metadata={
                    "campaign_id": campaign_id,
                    "contact_name": conversation.contact_name,
                    "conversation_id": conversation.id
                }
            )
            
            if result["success"]:
                conversation.external_conversation_id = result["call"]["conversation_id"]
                conversation.status = "in_progress"
                successful_calls += 1
            else:
                conversation.status = "failed"
                failed_calls += 1
                
        except Exception as e:
            conversation.status = "failed"
            failed_calls += 1
            print(f"Failed to make call to {conversation.phone_number}: {e}")
        
        db.commit()
    
    # Update campaign statistics
    campaign.completed_calls = successful_calls + failed_calls
    campaign.successful_calls = successful_calls
    campaign.failed_calls = failed_calls
    
    if successful_calls + failed_calls >= len(conversations):
        campaign.status = "completed"
    
    db.commit()
    
    return {
        "message": "Voice campaign launched successfully",
        "successful_calls": successful_calls,
        "failed_calls": failed_calls,
        "note": "Limited to 5 calls for testing"
    }

@router.get("/{campaign_id}/conversations")
async def get_campaign_conversations(
    campaign_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get all conversations for a voice campaign (white-label)"""
    campaign = db.query(models.Campaign)\
        .filter(models.Campaign.id == campaign_id, models.Campaign.user_id == current_user.id)\
        .first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Voice campaign not found")
    
    conversations = db.query(models.Conversation)\
        .filter(models.Conversation.campaign_id == campaign_id)\
        .order_by(models.Conversation.created_at.desc()).all()
    
    return [
        {
            "id": conv.id,
            "phone_number": conv.phone_number,
            "contact_name": conv.contact_name,
            "status": conv.status,
            "duration_seconds": conv.duration_seconds,
            "created_at": conv.created_at.isoformat(),
            "transcript": conv.transcript
        }
        for conv in conversations
    ]

@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Delete voice campaign (white-label)"""
    campaign = db.query(models.Campaign)\
        .filter(models.Campaign.id == campaign_id, models.Campaign.user_id == current_user.id)\
        .first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Voice campaign not found")
    
    # Delete campaign (conversations will be deleted via cascade)
    db.delete(campaign)
    db.commit()
    
    return {"message": "Voice campaign deleted successfully"}

# NEW: Batch operations for single calls
@router.post("/api/batch-single-calls")
async def make_batch_single_calls(
    calls: List[SingleCallRequest],
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Make multiple single calls at once"""
    if len(calls) > 10:  # Limit batch size
        raise HTTPException(status_code=400, detail="Maximum 10 calls per batch")
    
    results = []
    
    for call_request in calls:
        try:
            result = await make_single_call(call_request, current_user, db)
            results.append({
                "phone_number": call_request.phone_number,
                "success": True,
                "conversation_id": result["conversation_id"]
            })
        except Exception as e:
            results.append({
                "phone_number": call_request.phone_number,
                "success": False,
                "error": str(e)
            })
    
    successful = len([r for r in results if r["success"]])
    failed = len(results) - successful
    
    return {
        "message": f"Batch completed: {successful} successful, {failed} failed",
        "results": results,
        "summary": {
            "total": len(calls),
            "successful": successful,
            "failed": failed
        }
    }