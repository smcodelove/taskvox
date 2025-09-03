# app/plivo_client.py - PLIVO + ELEVENLABS INTEGRATION

import os
import plivo
import requests
import base64
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class PlivoClient:
    def __init__(self, auth_id: str = None, auth_token: str = None):
        self.auth_id = auth_id or os.getenv("PLIVO_AUTH_ID")
        self.auth_token = auth_token or os.getenv("PLIVO_AUTH_TOKEN")
        self.from_number = os.getenv("PLIVO_FROM_NUMBER", "+918035736994")
        
        # ElevenLabs AI answer URL - will handle conversation
        self.answer_url = os.getenv("ELEVENLABS_ANSWER_URL", "https://api.elevenlabs.io/v1/convai/conversations/phone/answer")
        self.hangup_url = os.getenv("PLIVO_HANGUP_URL", "http://localhost:8000/api/plivo/hangup")
        
        if not all([self.auth_id, self.auth_token]):
            raise ValueError("Plivo credentials missing. Get them from https://console.plivo.com/")
        
        try:
            self.client = plivo.RestClient(self.auth_id, self.auth_token)
            logger.info("Plivo client initialized for AI calls")
        except Exception as e:
            logger.error(f"Plivo client initialization failed: {e}")
            self.client = None
    
    async def make_ai_call(self, to_number: str, elevenlabs_agent_id: str, agent_data: Dict = None) -> Dict:
        """Make call that connects to ElevenLabs AI agent"""
        try:
            if not self.client:
                return {"success": False, "error": "Plivo client not initialized"}
            
            # Clean phone number
            to_number = to_number.strip()
            if not to_number.startswith('+'):
                to_number = '+' + to_number
            
            # Build answer URL with ElevenLabs agent parameters
            answer_url = f"{self.answer_url}?agent_id={elevenlabs_agent_id}"
            
            # Add metadata as URL parameters
            if agent_data:
                url_params = []
                for key, value in agent_data.items():
                    if value:
                        url_params.append(f"{key}={value}")
                if url_params:
                    answer_url += "&" + "&".join(url_params)
            
            # Plivo call parameters for AI integration
            call_params = {
                'from_': self.from_number,
                'to_': to_number,
                'answer_url': answer_url,
                'answer_method': 'POST',  # ElevenLabs expects POST
                'hangup_url': self.hangup_url,
                'hangup_method': 'POST',
                'machine_detection': 'true'
            }
            
            logger.info(f"Making AI call: {self.from_number} → {to_number}")
            logger.info(f"AI Answer URL: {answer_url}")
            
            # Make the call
            response = self.client.calls.create(**call_params)
            
            # Extract call UUID
            call_uuid = None
            if hasattr(response, 'call_uuid'):
                call_uuid = response.call_uuid
            elif hasattr(response, 'uuid'):
                call_uuid = response.uuid
            else:
                import uuid
                call_uuid = str(uuid.uuid4())
            
            return {
                "success": True,
                "call_uuid": call_uuid,
                "message": "AI call initiated - Plivo + ElevenLabs",
                "from_number": self.from_number,
                "to_number": to_number,
                "ai_agent_id": elevenlabs_agent_id
            }
            
        except Exception as e:
            logger.error(f"AI call failed: {e}")
            return {"success": False, "error": f"AI call failed: {str(e)}"}
    
    def verify_credentials(self) -> Dict:
        """Test Plivo credentials"""
        try:
            auth_string = f"{self.auth_id}:{self.auth_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'https://api.plivo.com/v1/Account/{self.auth_id}/',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "account_name": data.get('name', 'Plivo Account'),
                    "account_id": self.auth_id,
                    "cash_credits": data.get('cash_credits', '0.00'),
                    "message": "Plivo verified - Ready for AI calls"
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error {response.status_code}"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}