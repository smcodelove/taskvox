"""
TasKvox AI - Campaigns Router
"""
import io
import csv
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.elevenlabs_client import ElevenLabsClient

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
async def campaigns_page(
    request: Request,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Campaigns management page"""
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

@router.get("/api", response_model=List[schemas.Campaign])
async def get_campaigns_api(
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all campaigns for current user"""
    campaigns = db.query(models.Campaign)\
        .filter(models.Campaign.user_id == current_user.id)\
        .order_by(models.Campaign.created_at.desc()).all()
    return campaigns

@router.post("/api", response_model=schemas.Campaign)
async def create_campaign_api(
    campaign: schemas.CampaignCreate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create new campaign via API"""
    return await create_campaign_internal(campaign, current_user, db)

@router.post("")
async def create_campaign_form(
    request: Request,
    name: str = Form(...),
    agent_id: int = Form(...),
    csv_file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create campaign from form submission"""
    try:
        # Validate CSV file
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read and parse CSV
        content = await csv_file.read()
        csv_content = content.decode('utf-8')
        
        # Parse CSV using built-in csv module
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        # Get fieldnames and validate required columns
        fieldnames = csv_reader.fieldnames or []
        required_columns = ['phone_number']
        missing_columns = [col for col in required_columns if col not in fieldnames]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"CSV missing required columns: {', '.join(missing_columns)}"
            )
        
        # Create campaign
        campaign_data = schemas.CampaignCreate(name=name, agent_id=agent_id)
        campaign = await create_campaign_internal(campaign_data, current_user, db)
        
        # Process contacts and create conversations
        contacts_processed = 0
        for row in csv_reader:
            phone_number = str(row.get('phone_number', '')).strip()
            contact_name = str(row.get('name', '')).strip() if 'name' in row else None
            
            if phone_number and phone_number != 'nan' and phone_number:
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
        
        return RedirectResponse(url="/campaigns", status_code=302)
        
    except Exception as e:
        campaigns = db.query(models.Campaign)\
            .filter(models.Campaign.user_id == current_user.id).all()
        agents = db.query(models.Agent)\
            .filter(models.Agent.user_id == current_user.id, models.Agent.is_active == True).all()
        
        return templates.TemplateResponse(
            "campaigns.html",
            {
                "request": request,
                "title": "Voice Campaigns - TasKvox AI",
                "user": current_user,
                "campaigns": campaigns,
                "agents": agents,
                "error": str(e)
            }
        )

async def create_campaign_internal(
    campaign: schemas.CampaignCreate,
    current_user: models.User,
    db: Session
) -> models.Campaign:
    """Internal function to create campaign"""
    
    # Verify agent exists and belongs to user
    agent = db.query(models.Agent)\
        .filter(models.Agent.id == campaign.agent_id, models.Agent.user_id == current_user.id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create campaign in database
    db_campaign = models.Campaign(
        user_id=current_user.id,
        agent_id=campaign.agent_id,
        name=campaign.name,
        status="pending"
    )
    
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    
    return db_campaign

@router.get("/{campaign_id}", response_model=schemas.Campaign)
async def get_campaign(
    campaign_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific campaign"""
    campaign = db.query(models.Campaign)\
        .filter(models.Campaign.id == campaign_id, models.Campaign.user_id == current_user.id)\
        .first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return campaign

@router.put("/{campaign_id}", response_model=schemas.Campaign)
async def update_campaign(
    campaign_id: int,
    campaign_update: schemas.CampaignUpdate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update campaign"""
    campaign = db.query(models.Campaign)\
        .filter(models.Campaign.id == campaign_id, models.Campaign.user_id == current_user.id)\
        .first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Update fields
    if campaign_update.name is not None:
        campaign.name = campaign_update.name
    if campaign_update.status is not None:
        campaign.status = campaign_update.status
    if campaign_update.total_contacts is not None:
        campaign.total_contacts = campaign_update.total_contacts
    if campaign_update.completed_calls is not None:
        campaign.completed_calls = campaign_update.completed_calls
    if campaign_update.successful_calls is not None:
        campaign.successful_calls = campaign_update.successful_calls
    if campaign_update.failed_calls is not None:
        campaign.failed_calls = campaign_update.failed_calls
    
    db.commit()
    db.refresh(campaign)
    
    return campaign

@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete campaign"""
    campaign = db.query(models.Campaign)\
        .filter(models.Campaign.id == campaign_id, models.Campaign.user_id == current_user.id)\
        .first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Delete from database (conversations will be deleted via cascade)
    db.delete(campaign)
    db.commit()
    
    return {"message": "Campaign deleted successfully"}

@router.post("/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Launch campaign - start making calls"""
    campaign = db.query(models.Campaign)\
        .filter(models.Campaign.id == campaign_id, models.Campaign.user_id == current_user.id)\
        .first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != "pending":
        raise HTTPException(status_code=400, detail="Campaign can only be launched from pending status")
    
    # Check if user has ElevenLabs API key
    if not current_user.elevenlabs_api_key:
        raise HTTPException(
            status_code=400,
            detail="ElevenLabs API key not configured"
        )
    
    # Get agent
    agent = db.query(models.Agent).filter(models.Agent.id == campaign.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get pending conversations for this campaign
    conversations = db.query(models.Conversation)\
        .filter(models.Conversation.campaign_id == campaign_id, models.Conversation.status == "pending")\
        .all()
    
    if not conversations:
        raise HTTPException(status_code=400, detail="No contacts to call in this campaign")
    
    # Update campaign status
    campaign.status = "running"
    db.commit()
    
    # Initialize ElevenLabs client
    client = ElevenLabsClient(current_user.elevenlabs_api_key)
    
    # Start making calls (in a real app, this would be done asynchronously)
    successful_calls = 0
    failed_calls = 0
    
    for conversation in conversations:
        try:
            # Make phone call
            result = await client.make_phone_call(
                agent.elevenlabs_agent_id,
                conversation.phone_number
            )
            
            if result["success"]:
                # Update conversation with ElevenLabs conversation ID
                conversation.elevenlabs_conversation_id = result["call"]["conversation_id"]
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
    
    if successful_calls + failed_calls >= campaign.total_contacts:
        campaign.status = "completed"
    
    db.commit()
    
    return {
        "message": "Campaign launched successfully",
        "successful_calls": successful_calls,
        "failed_calls": failed_calls
    }

@router.get("/{campaign_id}/conversations")
async def get_campaign_conversations(
    campaign_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for a campaign"""
    campaign = db.query(models.Campaign)\
        .filter(models.Campaign.id == campaign_id, models.Campaign.user_id == current_user.id)\
        .first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
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

@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Pause a running campaign"""
    campaign = db.query(models.Campaign)\
        .filter(models.Campaign.id == campaign_id, models.Campaign.user_id == current_user.id)\
        .first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != "running":
        raise HTTPException(status_code=400, detail="Campaign is not running")
    
    campaign.status = "paused"
    db.commit()
    
    return {"message": "Campaign paused successfully"}

@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Resume a paused campaign"""
    campaign = db.query(models.Campaign)\
        .filter(models.Campaign.id == campaign_id, models.Campaign.user_id == current_user.id)\
        .first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != "paused":
        raise HTTPException(status_code=400, detail="Campaign is not paused")
    
    campaign.status = "running"
    db.commit()
    
    return {"message": "Campaign resumed successfully"}