# FILE: app/routers/agents.py
# REPLACE YOUR ENTIRE app/routers/agents.py WITH THIS

"""
TasKvox AI - Agents Router (White-Label Version)
No ElevenLabs references visible to client
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
    """Voice agents management page (white-label)"""
    
    # Get local agents from database
    local_agents = db.query(models.Agent)\
        .filter(models.Agent.user_id == current_user.id)\
        .order_by(models.Agent.created_at.desc()).all()
    
    # Get available voices if API key is configured
    voices = []
    
    if current_user.voice_api_key:  # CHANGED: White-label field
        client = ElevenLabsClient(current_user.voice_api_key)  # Internal only
        
        # Get voices
        voices_result = await client.get_voices()
        if voices_result["success"]:
            voices = voices_result["voices"]
    
    return templates.TemplateResponse(
        "agents.html",
        {
            "request": request,
            "title": "Voice Agents - TasKvox AI",
            "user": current_user,
            "agents": local_agents,
            "voices": voices
        }
    )

@router.post("/sync-voice-agents")  # CHANGED: White-label endpoint
async def sync_voice_agents(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Sync voice agents from external provider"""
    
    if not current_user.voice_api_key:  # CHANGED: White-label field
        raise HTTPException(status_code=400, detail="Voice AI API key not configured")
    
    try:
        client = ElevenLabsClient(current_user.voice_api_key)  # Internal only
        result = await client.list_agents()
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=f"Failed to fetch agents: {result.get('error', 'Unknown error')}")
        
        agents_data = result.get("agents", [])
        
        if isinstance(agents_data, dict):
            agents_data = agents_data.get("agents", [])
        
        synced_count = 0
        
        if isinstance(agents_data, list):
            for agent_item in agents_data:
                try:
                    if isinstance(agent_item, dict):
                        agent_id = agent_item.get("agent_id") or agent_item.get("id")
                        agent_name = agent_item.get("name", f"Voice Agent {agent_id[:8] if agent_id else 'Unknown'}")
                        voice_id = agent_item.get("voice_id")
                        
                        system_prompt = None
                        if "prompt" in agent_item:
                            prompt_data = agent_item["prompt"]
                            if isinstance(prompt_data, dict):
                                system_prompt = prompt_data.get("prompt")
                            else:
                                system_prompt = str(prompt_data)
                        elif "system_prompt" in agent_item:
                            system_prompt = agent_item["system_prompt"]
                    
                    if not agent_id:
                        continue
                    
                    # Check if already exists
                    existing = db.query(models.Agent)\
                        .filter(
                            models.Agent.user_id == current_user.id,
                            models.Agent.external_agent_id == agent_id  # CHANGED: White-label field
                        ).first()
                    
                    if not existing:
                        new_agent = models.Agent(
                            user_id=current_user.id,
                            external_agent_id=agent_id,  # CHANGED: White-label field
                            name=agent_name,
                            voice_id=voice_id,
                            system_prompt=system_prompt,
                            is_active=True
                        )
                        db.add(new_agent)
                        synced_count += 1
                        print(f"Added voice agent: {agent_name} ({agent_id})")
                        
                except Exception as e:
                    print(f"Error processing agent {agent_item}: {e}")
                    continue
        
        db.commit()
        
        return {
            "message": f"Successfully synced {synced_count} voice agents",
            "synced_count": synced_count,
            "total_external_agents": len(agents_data) if isinstance(agents_data, list) else 0
        }
        
    except Exception as e:
        print(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=f"Error syncing voice agents: {str(e)}")

@router.post("")
async def create_agent_form(
    request: Request,
    name: str = Form(...),
    voice_id: str = Form(...),
    system_prompt: str = Form(...),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Create voice agent (white-label)"""
    try:
        external_agent_id = None
        
        if current_user.voice_api_key:  # CHANGED: White-label field
            client = ElevenLabsClient(current_user.voice_api_key)  # Internal only
            
            result = await client.create_agent({
                "name": name,
                "voice_id": voice_id,
                "system_prompt": system_prompt
            })
            
            if result["success"]:
                agent_data = result.get("agent", {})
                external_agent_id = (
                    agent_data.get("agent_id") or 
                    agent_data.get("id") or 
                    agent_data.get("agentId")
                )
                print(f"✅ External voice agent created: {external_agent_id}")
            else:
                print(f"❌ External voice agent creation failed: {result.get('error', 'Unknown error')}")
        
        # Create in local database
        db_agent = models.Agent(
            user_id=current_user.id,
            external_agent_id=external_agent_id,  # CHANGED: White-label field
            name=name,
            voice_id=voice_id,
            system_prompt=system_prompt,
            is_active=True
        )
        
        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)
        
        if external_agent_id:
            success_msg = f"Voice agent created successfully!"
        else:
            success_msg = "Voice agent created locally (Voice AI connection needed for full functionality)"
        
        return RedirectResponse(url=f"/agents?success={success_msg}", status_code=302)
        
    except Exception as e:
        print(f"💥 Exception during voice agent creation: {e}")
        return RedirectResponse(url=f"/agents?error=Creation failed: {str(e)}", status_code=302)

@router.post("/{agent_id}/test-call")
async def test_agent_call(
    agent_id: int,
    phone_number: str = Form(...),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Test voice agent with phone call"""
    
    agent = db.query(models.Agent)\
        .filter(models.Agent.id == agent_id, models.Agent.user_id == current_user.id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Voice agent not found")
    
    if not current_user.voice_api_key:  # CHANGED: White-label field
        raise HTTPException(status_code=400, detail="Voice AI API key not configured")
    
    if not agent.external_agent_id:  # CHANGED: White-label field
        raise HTTPException(status_code=400, detail="Voice agent not linked to Voice AI service")
    
    try:
        client = ElevenLabsClient(current_user.voice_api_key)  # Internal only
        result = await client.make_single_call(
            agent.external_agent_id,  # CHANGED: White-label field
            phone_number
        )
        
        # Create conversation record
        conversation = models.Conversation(
            user_id=current_user.id,
            agent_id=agent.id,
            phone_number=phone_number,
            contact_name="Test Call",
            status="in_progress" if result["success"] else "failed"
        )
        
        if result["success"] and "call" in result:
            conversation.external_conversation_id = result["call"].get("conversation_id")  # CHANGED
        
        db.add(conversation)
        db.commit()
        
        if result["success"]:
            return {
                "message": "Test call initiated successfully!",
                "conversation_id": conversation.id
            }
        else:
            return {
                "message": f"Test call failed: {result.get('error', 'Unknown error')}",
                "conversation_id": conversation.id
            }
            
    except Exception as e:
        conversation = models.Conversation(
            user_id=current_user.id,
            agent_id=agent.id,
            phone_number=phone_number,
            contact_name="Test Call",
            status="failed"
        )
        db.add(conversation)
        db.commit()
        
        raise HTTPException(status_code=400, detail=f"Test call error: {str(e)}")

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Delete voice agent"""
    
    agent = db.query(models.Agent)\
        .filter(models.Agent.id == agent_id, models.Agent.user_id == current_user.id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Voice agent not found")
    
    # Delete from external service if exists
    if agent.external_agent_id and current_user.voice_api_key:  # CHANGED: White-label fields
        try:
            client = ElevenLabsClient(current_user.voice_api_key)  # Internal only
            await client.delete_agent(agent.external_agent_id)  # CHANGED: White-label field
        except Exception as e:
            print(f"Failed to delete from external Voice AI service: {e}")
    
    # Delete from database
    db.delete(agent)
    db.commit()
    
    return {"message": "Voice agent deleted successfully"}

@router.get("/api/voices")
async def get_voices(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie)
):
    """Get available voice profiles"""
    if not current_user.voice_api_key:  # CHANGED: White-label field
        raise HTTPException(status_code=400, detail="Voice AI API key not configured")
    
    client = ElevenLabsClient(current_user.voice_api_key)  # Internal only
    result = await client.get_voices()
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get voice profiles: {result['error']}"
        )
    
    return result["voices"]