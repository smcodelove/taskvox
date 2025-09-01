"""
TasKvox AI - Updated ElevenLabs API Client (2025)
Supports latest Conversational AI 2.0 features including batch calling
"""
import httpx
from typing import Dict, List, Optional, Any
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ElevenLabsClient:
    """Updated client for ElevenLabs Conversational AI API (2025)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
    
    async def test_connection(self) -> Dict:
        """Test API connection with user subscription info"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/user/subscription",
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_voices(self) -> Dict:
        """Get available voices"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"success": True, "voices": response.json()["voices"]}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_agent(self, config: Dict) -> Dict:
        """Create new conversational agent with latest API"""
        try:
            agent_config = {
                "name": config.get("name", "TasKvox Agent"),
                "voice_id": config.get("voice_id"),
                "conversation_config": {
                    "agent": {
                        "prompt": {
                            "prompt": config.get("system_prompt", "You are a helpful AI assistant.")
                        },
                        "language": config.get("language", "en")
                    }
                },
                "widget_config": {
                    "layout": "floating_button",
                    "avatar_url": config.get("avatar_url"),
                    "greeting_message": config.get("greeting", "Hello! How can I help you today?")
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/convai/agents",
                    headers=self.headers,
                    json=agent_config,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    return {"success": True, "agent": response.json()}
                else:
                    error_msg = response.text
                    logger.error(f"Failed to create agent: {error_msg}")
                    return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_agents(self) -> Dict:
        """List all user agents"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/convai/agents",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {"success": True, "agents": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_agent(self, agent_id: str) -> Dict:
        """Get specific agent details"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/convai/agents/{agent_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {"success": True, "agent": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to get agent: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_agent(self, agent_id: str, updates: Dict) -> Dict:
        """Update agent configuration"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/convai/agents/{agent_id}",
                    headers=self.headers,
                    json=updates,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return {"success": True, "agent": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to update agent: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_agent(self, agent_id: str) -> Dict:
        """Delete an agent"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/convai/agents/{agent_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {"success": True}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to delete agent: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_batch_call(self, batch_config: Dict) -> Dict:
        """Create batch calling campaign (NEW 2025 feature)"""
        try:
            config = {
                "agent_id": batch_config["agent_id"],
                "phone_numbers": batch_config["phone_numbers"],  # List of phone numbers
                "name": batch_config.get("name", f"Batch Call - {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
                "description": batch_config.get("description", ""),
                "schedule": batch_config.get("schedule", "immediate"),  # "immediate" or datetime
                "max_concurrent_calls": batch_config.get("max_concurrent_calls", 10),
                "retry_config": {
                    "max_retries": batch_config.get("max_retries", 2),
                    "retry_delay_minutes": batch_config.get("retry_delay_minutes", 60)
                }
            }
            
            # Add personalization if provided
            if batch_config.get("personalization"):
                config["personalization"] = batch_config["personalization"]
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/convai/batch-calls",
                    headers=self.headers,
                    json=config,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    return {"success": True, "batch": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to create batch call: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_batch_call_status(self, batch_id: str) -> Dict:
        """Get status of batch calling campaign"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/convai/batch-calls/{batch_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {"success": True, "batch": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to get batch status: {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_batch_call(self, batch_id: str) -> Dict:
        """Cancel a running batch call campaign"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/convai/batch-calls/{batch_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {"success": True}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to cancel batch call: {e}")
            return {"success": False, "error": str(e)}
    
    async def make_single_call(self, agent_id: str, phone_number: str, metadata: Dict = None) -> Dict:
        """Make a single phone call (updated endpoint)"""
        try:
            call_config = {
                "agent_id": agent_id,
                "phone_number": phone_number
            }
            
            if metadata:
                call_config["metadata"] = metadata
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/convai/phone-calls",
                    headers=self.headers,
                    json=call_config,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    return {"success": True, "call": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to make phone call: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_conversation(self, conversation_id: str) -> Dict:
        """Get conversation details with transcript"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/convai/conversations/{conversation_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {"success": True, "conversation": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_conversation_audio(self, conversation_id: str) -> Dict:
        """Get conversation audio URL"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/convai/conversations/{conversation_id}/audio",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    audio_data = response.json()
                    return {"success": True, "audio_url": audio_data.get("audio_url")}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to get conversation audio: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_conversations(self, agent_id: Optional[str] = None, limit: int = 100) -> Dict:
        """List conversations with optional filtering"""
        try:
            params = {"limit": limit}
            if agent_id:
                params["agent_id"] = agent_id
                
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/convai/conversations",
                    headers=self.headers,
                    params=params,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {"success": True, "conversations": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return {"success": False, "error": str(e)}
    
    # Knowledge Base methods (for RAG functionality)
    async def create_knowledge_base(self, name: str, description: str = "") -> Dict:
        """Create a knowledge base for RAG"""
        try:
            config = {
                "name": name,
                "description": description
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/convai/knowledge-bases",
                    headers=self.headers,
                    json=config,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    return {"success": True, "knowledge_base": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to create knowledge base: {e}")
            return {"success": False, "error": str(e)}
    
    async def add_document_to_kb(self, kb_id: str, document_data: Dict) -> Dict:
        """Add document to knowledge base"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/convai/knowledge-bases/{kb_id}/documents",
                    headers=self.headers,
                    json=document_data,
                    timeout=60.0
                )
                
                if response.status_code == 201:
                    return {"success": True, "document": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            logger.error(f"Failed to add document to KB: {e}")
            return {"success": False, "error": str(e)}