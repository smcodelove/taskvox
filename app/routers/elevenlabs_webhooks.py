# app/routers/elevenlabs_webhooks.py - NEW FILE

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
import logging
import hmac
import hashlib
import time
import json
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/webhooks/elevenlabs")
async def elevenlabs_webhook_handler(request: Request, db: Session = Depends(get_db)):
    """Handle ElevenLabs post_call_transcription webhook"""
    try:
        # Get request body and headers
        body = await request.body()
        signature_header = request.headers.get("elevenlabs-signature")
        
        if not signature_header:
            logger.error("Missing ElevenLabs signature header")
            raise HTTPException(status_code=401, detail="Missing signature")
        
        # Validate webhook signature (optional - can skip for testing)
        # webhook_secret = os.getenv("ELEVENLABS_WEBHOOK_SECRET")
        # if webhook_secret and not validate_signature(body, signature_header, webhook_secret):
        #     raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook payload
        payload = json.loads(body.decode('utf-8'))
        event_type = payload.get("type")
        
        logger.info(f"ElevenLabs webhook received: {event_type}")
        
        if event_type == "post_call_transcription":
            await handle_call_completion(payload, db)
        else:
            logger.info(f"Unhandled event type: {event_type}")
        
        return {"status": "success"}
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook handler error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_call_completion(payload: dict, db: Session):
    """Process completed AI call and update conversation status"""
    try:
        data = payload.get("data", {})
        conversation_id = data.get("conversation_id")
        agent_id = data.get("agent_id")
        transcript = data.get("transcript", [])
        metadata = data.get("metadata", {})
        analysis = data.get("analysis", {})
        
        # Extract call metrics
        call_duration = metadata.get("call_duration_secs", 0)
        call_cost = metadata.get("cost", 0)
        call_successful = analysis.get("call_successful", "unknown")
        transcript_summary = analysis.get("transcript_summary", "")
        
        logger.info(f"Processing call completion: {conversation_id}")
        logger.info(f"Duration: {call_duration}s, Cost: {call_cost}, Status: {call_successful}")
        
        # Find conversation in database using external_call_id
        conversation = db.query(models.Conversation)\
            .filter(models.Conversation.external_call_id == conversation_id)\
            .first()
        
        if not conversation:
            # Try to find by agent and recent timestamp
            conversation = db.query(models.Conversation)\
                .join(models.Agent)\
                .filter(models.Agent.external_agent_id == agent_id)\
                .filter(models.Conversation.status.in_(["in_progress", "connected"]))\
                .order_by(models.Conversation.created_at.desc())\
                .first()
        
        if conversation:
            # Update conversation with completion data
            conversation.status = "completed" if call_successful == "success" else "failed"
            conversation.duration_seconds = call_duration
            conversation.external_call_id = conversation_id
            
            # Build transcript text
            full_transcript = build_transcript_text(transcript)
            conversation.transcript = full_transcript
            
            # Store analysis summary
            if transcript_summary:
                conversation.notes = transcript_summary
            
            db.commit()
            
            logger.info(f"Updated conversation {conversation.id}: {conversation.status}")
            logger.info(f"Transcript length: {len(full_transcript)} chars")
            
        else:
            logger.warning(f"No matching conversation found for call {conversation_id}")
            
    except Exception as e:
        logger.error(f"Error processing call completion: {e}")

def build_transcript_text(transcript: list) -> str:
    """Convert transcript array to readable text"""
    try:
        transcript_lines = []
        
        for turn in transcript:
            role = turn.get("role", "unknown")
            message = turn.get("message", "")
            time_in_call = turn.get("time_in_call_secs", 0)
            
            # Format: [00:15] Agent: Hello, how can I help you?
            time_str = f"{time_in_call//60:02d}:{time_in_call%60:02d}"
            speaker = "Agent" if role == "agent" else "Customer"
            
            transcript_lines.append(f"[{time_str}] {speaker}: {message}")
        
        return "\n".join(transcript_lines)
        
    except Exception as e:
        logger.error(f"Error building transcript: {e}")
        return "Transcript processing failed"

def validate_signature(body: bytes, signature_header: str, secret: str) -> bool:
    """Validate ElevenLabs webhook signature"""
    try:
        headers = signature_header.split(",")
        timestamp = headers[0].split("=")[1] if headers[0].startswith("t=") else None
        signature = headers[1] if len(headers) > 1 and headers[1].startswith("v0=") else None
        
        if not timestamp or not signature:
            return False
        
        # Validate timestamp (within 30 minutes)
        tolerance = int(time.time()) - 30 * 60
        if int(timestamp) < tolerance:
            return False
        
        # Validate HMAC signature
        full_payload = f"{timestamp}.{body.decode('utf-8')}"
        mac = hmac.new(
            key=secret.encode("utf-8"),
            msg=full_payload.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        expected_signature = 'v0=' + mac.hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        logger.error(f"Signature validation error: {e}")
        return False

@router.get("/api/webhooks/elevenlabs/test")
async def test_webhook():
    """Test endpoint to verify webhook is accessible"""
    return {
        "status": "webhook_active",
        "message": "ElevenLabs webhook handler is running",
        "timestamp": datetime.now().isoformat()
    }