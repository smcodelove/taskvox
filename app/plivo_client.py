# Ye new file banao: app/plivo_client.py
# Poora ye code copy-paste karo:

import os
import plivo
import httpx
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class PlivoClient:
    def __init__(self, auth_id: str = None, auth_token: str = None):
        self.auth_id = auth_id or os.getenv("PLIVO_AUTH_ID")
        self.auth_token = auth_token or os.getenv("PLIVO_AUTH_TOKEN")
        self.from_number = os.getenv("PLIVO_FROM_NUMBER")
        self.answer_url = os.getenv("PLIVO_ANSWER_URL")
        
        if not all([self.auth_id, self.auth_token, self.from_number]):
            raise ValueError("Plivo credentials not configured")
        
        self.client = plivo.RestClient(self.auth_id, self.auth_token)
    
    async def make_call(self, to_number: str, agent_data: Dict = None) -> Dict:
        """Make outbound call using Plivo"""
        try:
            # Plivo call parameters
            call_params = {
                'from': self.from_number,
                'to': to_number,
                'answer_url': self.answer_url,
                'answer_method': 'GET'
            }
            
            # Add metadata if provided
            if agent_data:
                # You can add custom parameters here
                call_params['machine_detection'] = 'true'
            
            # Make the call
            response = self.client.calls.create(**call_params)
            
            return {
                "success": True,
                "call_uuid": response.call_uuid,
                "message": "Call initiated successfully"
            }
            
        except Exception as e:
            logger.error(f"Plivo call failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_credentials(self) -> Dict:
        """Test Plivo credentials"""
        try:
            account = self.client.accounts.get()
            return {
                "success": True,
                "account_name": account.name,
                "account_id": account.account_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }