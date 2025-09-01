"""
TasKvox AI - ElevenLabs API Client
"""
import httpx
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ElevenLabsClient:
    """Client for ElevenLabs Conversational AI API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
    
    async def test_connection(self) -> Dict:
        """Test API connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/user",
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
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
                    return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_agent(self, config: Dict) -> Dict:
        """Create new conversational agent"""
        try:
            agent_config = {
                "conversation_config": {
                    "agent": {
                        "prompt": {
                            "prompt": config.get("system_prompt", "You are a helpful AI assistant.")
                        }
                    }
                },
                "platform_settings": {
                    "widget_config": {
                        "layout": "full_screen"
                    }
                },
                "name": config.get("name", "TasKvox Agent"),
                "voice_id": config.get("voice_id")
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
                    return {"success": False, "error": f"HTTP {response.status_code}"}
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
                    return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Failed to get agent: {e}")
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
                    return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Failed to delete agent: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_phone_number(self, agent_id: str, phone_number_id: Optional[str] = None) -> Dict:
        """Create phone number for agent"""
        try:
            config = {
                "agent_id": agent_id
            }
            if phone_number_id:
                config["phone_number_id"] = phone_number_id
                
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/convai/phone-numbers",
                    headers=self.headers,
                    json=config,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    return {"success": True, "phone_number": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Failed to create phone number: {e}")
            return {"success": False, "error": str(e)}
    
    async def make_phone_call(self, agent_id: str, customer_phone_number: str) -> Dict:
        """Make a phone call"""
        try:
            call_config = {
                "agent_id": agent_id,
                "customer_phone_number": customer_phone_number
            }
            
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
                    return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Failed to make phone call: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_conversation(self, conversation_id: str) -> Dict:
        """Get conversation details"""
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
                    return {"success": False, "error": f"HTTP {response.status_code}"}
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
                    return {"success": True, "audio": response.json()}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Failed to get conversation audio: {e}")
            return {"success": False, "error": str(e)}