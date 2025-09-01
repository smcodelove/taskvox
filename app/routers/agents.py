# FILE PATH: app/routers/agents.py
# REPLACE YOUR EXISTING app/routers/agents.py WITH THIS

"""
TasKvox AI - Agents Router with Working ElevenLabs Sync
Path: app/routers/agents.py
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
        
        # Get existing ElevenLabs agents for sync button
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
            "elevenlabs_agents": elevenlabs_agents
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
    
    try:
        client = ElevenLabsClient(current_user.elevenlabs_api_key)
        result = await client.list_agents()
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=f"Failed to fetch agents: {result.get('error', 'Unknown error')}")
        
        # Get agents list from response
        agents_data = result.get("agents", [])
        
        # Handle different response structures
        if isinstance(agents_data, dict):
            agents_data = agents_data.get("agents", [])
        
        synced_count = 0
        
        # Debug print
        print(f"ElevenLabs response: {result}")
        print(f"Agents data type: {type(agents_data)}")
        print(f"Agents data: {agents_data}")
        
        # Handle the response properly
        if isinstance(agents_data, list):
            for agent_item in agents_data:
                try:
                    # Handle different agent formats
                    if isinstance(agent_item, dict):
                        agent_id = agent_item.get("agent_id") or agent_item.get("id")
                        agent_name = agent_item.get("name", f"Agent {agent_id[:8] if agent_id else 'Unknown'}")
                        voice_id = agent_item.get("voice_id")
                        
                        # Handle nested prompt
                        system_prompt = None
                        if "prompt" in agent_item:
                            prompt_data = agent_item["prompt"]
                            if isinstance(prompt_data, dict):
                                system_prompt = prompt_data.get("prompt")
                            else:
                                system_prompt = str(prompt_data)
                        elif "system_prompt" in agent_item:
                            system_prompt = agent_item["system_prompt"]
                        
                    elif isinstance(agent_item, str):
                        # If it's just an ID string
                        agent_id = agent_item
                        agent_name = f"Imported Agent {agent_id[:8]}"
                        voice_id = None
                        system_prompt = None
                    else:
                        continue
                    
                    if not agent_id:
                        continue
                    
                    # Check if already exists
                    existing = db.query(models.Agent)\
                        .filter(
                            models.Agent.user_id == current_user.id,
                            models.Agent.elevenlabs_agent_id == agent_id
                        ).first()
                    
                    if not existing:
                        new_agent = models.Agent(
                            user_id=current_user.id,
                            elevenlabs_agent_id=agent_id,
                            name=agent_name,
                            voice_id=voice_id,
                            system_prompt=system_prompt,
                            is_active=True
                        )
                        db.add(new_agent)
                        synced_count += 1
                        print(f"Added agent: {agent_name} ({agent_id})")
                        
                except Exception as e:
                    print(f"Error processing agent {agent_item}: {e}")
                    continue
        
        db.commit()
        
        return {
            "message": f"Successfully synced {synced_count} agents from ElevenLabs",
            "synced_count": synced_count,
            "total_elevenlabs_agents": len(agents_data) if isinstance(agents_data, list) else 0
        }
        
    except Exception as e:
        print(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=f"Error syncing agents: {str(e)}")

# FILE PATH: app/routers/agents.py
# UPDATE YOUR create_agent_form FUNCTION WITH THIS DEBUG VERSION

@router.post("")
async def create_agent_form(
    request: Request,
    name: str = Form(...),
    voice_id: str = Form(...),
    system_prompt: str = Form(...),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Create agent from form submission with detailed debugging"""
    try:
        elevenlabs_agent_id = None
        error_message = None
        
        if current_user.elevenlabs_api_key:
            # Try to create in ElevenLabs with detailed logging
            client = ElevenLabsClient(current_user.elevenlabs_api_key)
            
            print(f"🔍 Creating agent in ElevenLabs...")
            print(f"   Name: {name}")
            print(f"   Voice ID: {voice_id}")
            print(f"   System Prompt: {system_prompt[:100]}...")
            
            result = await client.create_agent({
                "name": name,
                "voice_id": voice_id,
                "system_prompt": system_prompt
            })
            
            print(f"📡 ElevenLabs API Response:")
            print(f"   Success: {result['success']}")
            print(f"   Full Response: {result}")
            
            if result["success"]:
                # Extract agent ID with multiple fallback options
                agent_data = result.get("agent", {})
                print(f"   Agent Data: {agent_data}")
                
                if isinstance(agent_data, dict):
                    elevenlabs_agent_id = (
                        agent_data.get("agent_id") or 
                        agent_data.get("id") or 
                        agent_data.get("agentId")
                    )
                elif isinstance(agent_data, str):
                    elevenlabs_agent_id = agent_data
                
                print(f"   Extracted Agent ID: {elevenlabs_agent_id}")
                
                if not elevenlabs_agent_id:
                    print("❌ Could not extract agent ID from response")
                    error_message = "Agent created but no ID returned from ElevenLabs"
            else:
                error_message = result.get('error', 'Unknown ElevenLabs error')
                print(f"❌ ElevenLabs creation failed: {error_message}")
        else:
            print("⚠️  No API key - creating local agent only")
        
        # Create in local database regardless
        db_agent = models.Agent(
            user_id=current_user.id,
            elevenlabs_agent_id=elevenlabs_agent_id,
            name=name,
            voice_id=voice_id,
            system_prompt=system_prompt,
            is_active=True
        )
        
        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)
        
        print(f"✅ Local agent created with ID: {db_agent.id}")
        
        # Determine success message
        if elevenlabs_agent_id:
            status_msg = f"Agent created successfully (ElevenLabs ID: {elevenlabs_agent_id[:12]}...)"
        elif error_message:
            status_msg = f"Agent created locally but ElevenLabs failed: {error_message}"
        else:
            status_msg = "Agent created (local only - configure API key for ElevenLabs sync)"
        
        return RedirectResponse(url=f"/agents?success={status_msg}", status_code=302)
        
    except Exception as e:
        print(f"💥 Exception during agent creation: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=f"/agents?error=Creation failed: {str(e)}", status_code=302)

@router.post("/{agent_id}/test-call")
async def test_agent_call(
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
        raise HTTPException(status_code=400, detail="ElevenLabs API key not configured")
    
    if not agent.elevenlabs_agent_id:
        raise HTTPException(status_code=400, detail="Agent not linked to ElevenLabs")
    
    try:
        # Make test call
        client = ElevenLabsClient(current_user.elevenlabs_api_key)
        result = await client.make_single_call(
            agent.elevenlabs_agent_id,
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
            conversation.elevenlabs_conversation_id = result["call"].get("conversation_id")
        
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
        # Create failed conversation record
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
    """Delete agent"""
    
    agent = db.query(models.Agent)\
        .filter(models.Agent.id == agent_id, models.Agent.user_id == current_user.id)\
        .first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Delete from ElevenLabs if exists
    if agent.elevenlabs_agent_id and current_user.elevenlabs_api_key:
        try:
            client = ElevenLabsClient(current_user.elevenlabs_api_key)
            await client.delete_agent(agent.elevenlabs_agent_id)
        except Exception as e:
            print(f"Failed to delete from ElevenLabs: {e}")
    
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