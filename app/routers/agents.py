"""
TasKvox AI - Enhanced Agents Router
Fetch existing ElevenLabs agents and sync with database
Replace your app/routers/agents.py with this
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.elevenlabs_client import ElevenLabsClient

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
async def agents_page(
    request: Request,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Agents management page with ElevenLabs sync"""
    
    # Get local agents from database
    local_agents = db.query(models.Agent)\
        .filter(models.Agent.user_id == current_user.id)\
        .order_by(models.Agent.created_at.desc()).all()
    
    # Get available voices if API key is configured
    voices = []
    elevenlabs_agents = []
    
    if current_user.elevenlabs_api_key:
        client = ElevenLabsClient(current_user.elevenlabs_api_key)
        
        # Get voices
        voices_result = await client.get_voices()
        if voices_result["success"]:
            voices = voices_result["voices"]
        
        # Get existing ElevenLabs agents
        agents_result = await client.list_agents()
        if agents_result["success"]:
            elevenlabs_agents = agents_result.get("agents", [])
    
    return templates.TemplateResponse(
        "agents.html",
        {
            "request": request,
            "title": "AI Agents - TasKvox AI",
            "user": current_user,
            "agents": local_agents,
            "voices": voices,
            "elevenlabs_agents": elevenlabs_agents  # Pass ElevenLabs agents to template
        }
    )

@router.post("/sync-elevenlabs")
async def sync_elevenlabs_agents(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Sync existing ElevenLabs agents to local database"""
    
    if not current_user.elevenlabs_api_key:
        raise HTTPException(status_code=400, detail="ElevenLabs API key not configured")
    
    client = ElevenLabsClient(current_user.elevenlabs_api_key)
    result = await client.list_agents()
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=f"Failed to fetch agents: {result['error']}")
    
    elevenlabs_agents = result.get("agents", [])
    synced_count = 0
    
    for el_agent in elevenlabs_agents:
        # Check if agent already exists in our database
        existing_agent = db.query(models.Agent)\
            .filter(
                models.Agent.user_id == current_user.id,
                models.Agent.elevenlabs_agent_id == el_agent["agent_id"]
            ).first()
        
        if not existing_agent:
            # Create new agent record
            new_agent = models.Agent(
                user_id=current_user.id,
                elevenlabs_agent_id=el_agent["agent_id"],
                name=el_agent.get("name", "Imported Agent"),
                voice_id=el_agent.get("voice_id"),
                system_prompt=el_agent.get("prompt", {}).get("prompt"),
                is_active=True
            )
            db.add(new_agent)
            synced_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully synced {synced_count} agents from ElevenLabs",
        "synced_count": synced_count,
        "total_elevenlabs_agents": len(elevenlabs_agents)
    }

@router.post("")
async def create_agent_form(
    request: Request,
    name: str = Form(...),
    voice_id: str = Form(...),
    system_prompt: str = Form(...),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Create agent from form submission"""
    try:
        agent_data = schemas.AgentCreate(
            name=name,
            voice_id=voice_id,
            system_prompt=system_prompt
        )
        
        await create_agent_internal(agent_data, current_user, db)
        return RedirectResponse(url="/agents?success=Agent created successfully", status_code=302)
        
    except Exception as e:
        return RedirectResponse(url=f"/agents?error={str(e)}", status_code=302)

async def create_agent_internal(
    agent: schemas.AgentCreate,
    current_user: models.User,
    db: Session
) -> models.Agent:
    """Internal function to create agent"""
    
    # Check if user has ElevenLabs API key
    if not current_user.elevenlabs_api_key:
        raise HTTPException(
            status_code=400,
            detail="Please configure your ElevenLabs API key in settings first"
        )
    
    # Create agent in ElevenLabs
    client = ElevenLabsClient(current_user.elevenlabs_api_key)
    result = await client.create_agent({
        "name": agent.name,
        "voice_id": agent.voice_id,
        "system_prompt": agent.system_prompt
    })
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create agent in ElevenLabs: {result.get('error', 'Unknown error')}"
        )
    
    # Create agent in database
    db_agent = models.Agent(
        user_id=current_user.id,
        elevenlabs_agent_id=result["agent"]["agent_id"],
        name=agent.name,
        voice_id=agent.voice_id,
        system_prompt=agent.system_prompt
    )
    
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    
    return db_agent

@router.post("/{agent_id}/test-call")
async def test_agent_call(
    agent_id: int,
    phone_number: str = Form(...),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Test agent with a live phone call"""
    
    agent = db.query(models.Agent)\
        .filter(models.Agent.id == agent_id, models.Agent.user_id == current_user.id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not current_user.elevenlabs_api_key:
        raise HTTPException(status_code=400, detail="ElevenLabs API key not configured")
    
    if not agent.elevenlabs_agent_id:
        raise HTTPException(status_code=400, detail="Agent not linked to ElevenLabs")
    
    # Make test call using the updated client
    client = ElevenLabsClient(current_user.elevenlabs_api_key)
    result = await client.make_single_call(
        agent.elevenlabs_agent_id,
        phone_number
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to make test call: {result.get('error', 'Unknown error')}"
        )
    
    # Create conversation record
    conversation = models.Conversation(
        user_id=current_user.id,
        agent_id=agent.id,
        elevenlabs_conversation_id=result["call"]["conversation_id"],
        phone_number=phone_number,
        contact_name="Test Call",
        status="in_progress"
    )
    
    db.add(conversation)
    db.commit()
    
    return {
        "message": "Test call initiated successfully!",
        "conversation_id": conversation.id,
        "call_status": result["call"]["status"]
    }

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Delete agent"""
    
    agent = db.query(models.Agent)\
        .filter(models.Agent.id == agent_id, models.Agent.user_id == current_user.id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Delete from ElevenLabs if exists
    if agent.elevenlabs_agent_id and current_user.elevenlabs_api_key:
        client = ElevenLabsClient(current_user.elevenlabs_api_key)
        await client.delete_agent(agent.elevenlabs_agent_id)
    
    # Delete from database
    db.delete(agent)
    db.commit()
    
    return {"message": "Agent deleted successfully"}

@router.get("/api/voices")
async def get_voices(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie)
):
    """Get available voices from ElevenLabs"""
    if not current_user.elevenlabs_api_key:
        raise HTTPException(status_code=400, detail="ElevenLabs API key not configured")
    
    client = ElevenLabsClient(current_user.elevenlabs_api_key)
    result = await client.get_voices()
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get voices: {result['error']}"
        )
    
    return result["voices"]