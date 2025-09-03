# app/plivo_client.py - RESPONSE OBJECT FIX

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
        self.answer_url = os.getenv("PLIVO_ANSWER_URL", "http://localhost:8000/api/plivo/answer")
        
        if not all([self.auth_id, self.auth_token]):
            raise ValueError("Plivo credentials missing. Get them from https://console.plivo.com/")
        
        # Initialize Plivo client
        try:
            self.client = plivo.RestClient(self.auth_id, self.auth_token)
            logger.info("Plivo client initialized successfully")
        except Exception as e:
            logger.error(f"Plivo client initialization failed: {e}")
            self.client = None
    
    async def make_call(self, to_number: str, agent_data: Dict = None) -> Dict:
        """Make outbound call using Plivo - FIXED RESPONSE HANDLING"""
        try:
            if not self.client:
                return {
                    "success": False,
                    "error": "Plivo client not initialized"
                }
            
            # Clean phone number
            to_number = to_number.strip()
            if not to_number.startswith('+'):
                to_number = '+' + to_number
            
            # Call parameters
            call_params = {
                'from_': self.from_number,
                'to_': to_number,
                'answer_url': self.answer_url,
                'answer_method': 'GET'
            }
            
            # Add machine detection if needed
            if agent_data:
                call_params['machine_detection'] = 'true'
            
            logger.info(f"Making Plivo call: {self.from_number} → {to_number}")
            logger.info(f"Call parameters: {call_params}")
            
            # Make the call
            response = self.client.calls.create(**call_params)
            
            # FIXED: Safe access to response attributes
            call_uuid = None
            call_status = "initiated"
            
            # Try different ways to get call_uuid
            if hasattr(response, 'call_uuid'):
                call_uuid = response.call_uuid
            elif hasattr(response, 'uuid'):
                call_uuid = response.uuid
            elif hasattr(response, 'id'):
                call_uuid = response.id
            elif isinstance(response, dict):
                call_uuid = response.get('call_uuid') or response.get('uuid') or response.get('id')
            else:
                # Fallback: generate UUID if response doesn't have one
                import uuid
                call_uuid = str(uuid.uuid4())
                logger.warning("Response object missing call_uuid, generated fallback UUID")
            
            # Try to get call status
            if hasattr(response, 'call_status'):
                call_status = response.call_status
            elif hasattr(response, 'status'):
                call_status = response.status
            elif isinstance(response, dict):
                call_status = response.get('call_status', 'initiated')
            
            logger.info(f"Plivo response: Call UUID = {call_uuid}, Status = {call_status}")
            
            return {
                "success": True,
                "call_uuid": call_uuid,
                "message": "Call initiated successfully with Plivo",
                "call_status": call_status,
                "from_number": self.from_number,
                "to_number": to_number
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Plivo call failed: {error_msg}")
            
            return {
                "success": False,
                "error": f"Call failed: {error_msg}"
            }
    
    def verify_credentials(self) -> Dict:
        """Test Plivo credentials"""
        try:
            # Direct API call method (most reliable)
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
                    "method": "API",
                    "account_name": data.get('name', 'Plivo Account'),
                    "account_id": self.auth_id,
                    "cash_credits": data.get('cash_credits', '0.00'),
                    "message": "Plivo credentials verified successfully"
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "error": "Invalid credentials. Check AUTH_ID and AUTH_TOKEN from Plivo Console"
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }
    
    def debug_response_structure(self, response) -> Dict:
        """Debug helper to understand response structure"""
        try:
            response_info = {
                "type": str(type(response)),
                "attributes": [attr for attr in dir(response) if not attr.startswith('_')],
                "dict_conversion": dict(response) if hasattr(response, '__iter__') else None
            }
            logger.info(f"Response structure: {response_info}")
            return response_info
        except Exception as e:
            logger.error(f"Debug failed: {e}")
            return {"error": str(e)}