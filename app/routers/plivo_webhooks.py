# app/routers/plivo_webhooks.py - NEW FILE

from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/plivo/hangup")
async def plivo_hangup_handler(request: Request, db: Session = Depends(get_db)):
    """Handle Plivo call hangup events"""
    try:
        # Get form data from Plivo
        form_data = await request.form()
        call_uuid = form_data.get("CallUUID")
        hangup_cause = form_data.get("HangupCause", "NORMAL_CLEARING")
        call_duration = form_data.get("Duration", "0")
        to_number = form_data.get("To")
        
        logger.info(f"Plivo hangup: {call_uuid}, Duration: {call_duration}s, Cause: {hangup_cause}, To: {to_number}")
        
        # Find conversation by call_uuid or phone number
        conversation = None
        
        if call_uuid:
            conversation = db.query(models.Conversation)\
                .filter(models.Conversation.external_call_id == call_uuid)\
                .first()
        
        # Fallback: find by phone number and recent timestamp
        if not conversation and to_number:
            conversation = db.query(models.Conversation)\
                .filter(models.Conversation.phone_number == to_number)\
                .filter(models.Conversation.status.in_(["in_progress", "connected", "initiating"]))\
                .order_by(models.Conversation.created_at.desc())\
                .first()
        
        if conversation:
            # Update conversation status based on hangup cause
            if hangup_cause in ["NORMAL_CLEARING", "USER_BUSY"]:
                conversation.status = "completed"
            else:
                conversation.status = "failed"
            
            # Update duration
            try:
                conversation.duration_seconds = int(call_duration)
            except:
                conversation.duration_seconds = 0
            
            db.commit()
            
            logger.info(f"Updated conversation {conversation.id} to {conversation.status}, duration: {call_duration}s")
        else:
            logger.warning(f"No conversation found for call {call_uuid} / {to_number}")
        
        return {"status": "success", "message": "Hangup processed"}
        
    except Exception as e:
        logger.error(f"Hangup handler error: {e}")
        return {"status": "error", "message": str(e)}