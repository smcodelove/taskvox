"""
TasKvox AI - Agents Router
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
    """Agents management page"""
    agents = db.query(models.Agent)\
        .filter(models.Agent.user_id == current_user.id)\
        .order_by(models.Agent.created_at.desc()).all()
    
    # Get available voices if API key is configured
    voices = []
    if current_user.elevenlabs_api_key:
        client = ElevenLabsClient(current_user.elevenlabs_api_key)
        voices_result = await client.get_voices()
        if voices_result["success"]:
            voices = voices_result["voices"]
    
    return templates.TemplateResponse(
        "agents.html",
        {
            "request": request,
            "title": "AI Agents - TasKvox AI",
            "user": current_user,
            "agents": agents,
            "voices": voices
        }
    )

@router.get("/api", response_model=List[schemas.Agent])
async def get_agents_api(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get all agents for current user"""
    agents = db.query(models.Agent)\
        .filter(models.Agent.user_id == current_user.id)\
        .order_by(models.Agent.created_at.desc()).all()
    return agents

@router.post("/api", response_model=schemas.Agent)
async def create_agent_api(
    agent: schemas.AgentCreate,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Create new agent via API"""
    return await create_agent_internal(agent, current_user, db)

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
        return RedirectResponse(url="/agents", status_code=302)
        
    except HTTPException as e:
        agents = db.query(models.Agent)\
            .filter(models.Agent.user_id == current_user.id).all()
        
        return templates.TemplateResponse(
            "agents.html",
            {
                "request": request,
                "title": "AI Agents - TasKvox AI",
                "user": current_user,
                "agents": agents,
                "error": str(e.detail)
            }
        )

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
            detail=f"Failed to create agent in ElevenLabs: {result['error']}"
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

@router.get("/{agent_id}", response_model=schemas.Agent)
async def get_agent(
    agent_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get specific agent"""
    agent = db.query(models.Agent)\
        .filter(models.Agent.id == agent_id, models.Agent.user_id == current_user.id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent

@router.put("/{agent_id}", response_model=schemas.Agent)
async def update_agent(
    agent_id: int,
    agent_update: schemas.AgentUpdate,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Update agent"""
    agent = db.query(models.Agent)\
        .filter(models.Agent.id == agent_id, models.Agent.user_id == current_user.id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update fields
    if agent_update.name is not None:
        agent.name = agent_update.name
    if agent_update.voice_id is not None:
        agent.voice_id = agent_update.voice_id
    if agent_update.system_prompt is not None:
        agent.system_prompt = agent_update.system_prompt
    if agent_update.is_active is not None:
        agent.is_active = agent_update.is_active
    
    db.commit()
    db.refresh(agent)
    
    return agent

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
        raise HTTPException(
            status_code=400,
            detail="ElevenLabs API key not configured"
        )
    
    client = ElevenLabsClient(current_user.elevenlabs_api_key)
    result = await client.get_voices()
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get voices: {result['error']}"
        )
    
    return result["voices"]

@router.post("/{agent_id}/test")
async def test_agent(
    agent_id: int,
    phone_number: str = Form(...),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Test agent with a phone call"""
    agent = db.query(models.Agent)\
        .filter(models.Agent.id == agent_id, models.Agent.user_id == current_user.id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not current_user.elevenlabs_api_key:
        raise HTTPException(
            status_code=400,
            detail="ElevenLabs API key not configured"
        )
    
    # Make test call
    client = ElevenLabsClient(current_user.elevenlabs_api_key)
    result = await client.make_phone_call(
        agent.elevenlabs_agent_id,
        phone_number
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to make test call: {result['error']}"
        )
    
    # Create conversation record
    conversation = models.Conversation(
        user_id=current_user.id,
        agent_id=agent.id,
        elevenlabs_conversation_id=result["call"]["conversation_id"],
        phone_number=phone_number,
        status="in_progress"
    )
    
    db.add(conversation)
    db.commit()
    
    return {
        "message": "Test call initiated successfully",
        "conversation_id": conversation.id,
        "call_id": result["call"]["call_id"]
    }