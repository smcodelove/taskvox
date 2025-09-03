# FILE: app/routers/settings.py
# REPLACE YOUR ENTIRE app/routers/settings.py WITH THIS

"""
TasKvox AI - Settings Router (White-Label Version)
Voice AI API Key Management and User Profile Settings
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..plivo_client import PlivoClient

from app.database import get_db
from app import models, schemas, auth
from app.elevenlabs_client import ElevenLabsClient

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Settings management page (white-label)"""
    
    # Test API key if it exists
    api_key_status = "Not configured"
    if current_user.voice_api_key:  # CHANGED: White-label field
        try:
            client = ElevenLabsClient(current_user.voice_api_key)  # Internal only
            test_result = await client.test_connection()
            if test_result["success"]:
                api_key_status = "✅ Connected"
            else:
                api_key_status = "❌ Connection Failed"
        except:
            api_key_status = "❌ Error"
    
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "title": "Settings - TasKvox AI",
            "user": current_user,
            "api_key_status": api_key_status,
            "has_api_key": bool(current_user.voice_api_key)  # CHANGED: White-label field
        }
    )

@router.post("/api-key")
async def update_api_key(
    request: Request,
    api_key: str = Form(...),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Update Voice AI API key (white-label)"""
    try:
        # Test the API key first
        client = ElevenLabsClient(api_key)  # Internal only
        test_result = await client.test_connection()
        
        if not test_result["success"]:
            return templates.TemplateResponse(
                "settings.html",
                {
                    "request": request,
                    "title": "Settings - TasKvox AI",
                    "user": current_user,
                    "error": f"Invalid Voice AI API key: {test_result.get('error', 'Connection failed')}",
                    "api_key_status": "❌ Connection Failed",
                    "has_api_key": bool(current_user.voice_api_key)  # CHANGED: White-label field
                }
            )
        
        # Update the API key
        current_user.voice_api_key = api_key  # CHANGED: White-label field
        db.commit()
        
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "title": "Settings - TasKvox AI",
                "user": current_user,
                "success": "Voice AI API key updated successfully!",
                "api_key_status": "✅ Connected",
                "has_api_key": True
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "title": "Settings - TasKvox AI",
                "user": current_user,
                "error": f"Error updating Voice AI API key: {str(e)}",
                "api_key_status": "❌ Error",
                "has_api_key": bool(current_user.voice_api_key)  # CHANGED: White-label field
            }
        )

@router.post("/profile")
async def update_profile(
    request: Request,
    email: str = Form(...),
    current_password: str = Form(None),
    new_password: str = Form(None),
    confirm_password: str = Form(None),
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Update user profile (white-label)"""
    try:
        # Update email if changed
        if email != current_user.email:
            # Check if email already exists
            existing_user = auth.get_user_by_email(db, email)
            if existing_user and existing_user.id != current_user.id:
                raise HTTPException(status_code=400, detail="Email already in use")
            current_user.email = email
        
        # Update password if provided
        if new_password:
            if not current_password:
                raise HTTPException(status_code=400, detail="Current password required")
            
            # Verify current password
            if not auth.verify_password(current_password, current_user.password_hash):
                raise HTTPException(status_code=400, detail="Current password incorrect")
            
            if new_password != confirm_password:
                raise HTTPException(status_code=400, detail="Passwords don't match")
            
            if len(new_password) < 6:
                raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
            
            # Update password
            current_user.password_hash = auth.get_password_hash(new_password)
        
        db.commit()
        
        return RedirectResponse(
            url="/settings?success=Profile updated successfully",
            status_code=302
        )
        
    except HTTPException as e:
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "title": "Settings - TasKvox AI",
                "user": current_user,
                "error": str(e.detail),
                "api_key_status": "✅ Connected" if current_user.voice_api_key else "Not configured",  # CHANGED
                "has_api_key": bool(current_user.voice_api_key)  # CHANGED: White-label field
            }
        )

@router.delete("/api-key")
async def remove_api_key(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Remove Voice AI API key (white-label)"""
    current_user.voice_api_key = None  # CHANGED: White-label field
    db.commit()
    return {"message": "Voice AI API key removed successfully"}

@router.get("/usage-stats")
async def get_usage_stats(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Get user usage statistics (white-label)"""
    
    total_agents = db.query(models.Agent).filter(
        models.Agent.user_id == current_user.id
    ).count()
    
    total_campaigns = db.query(models.Campaign).filter(
        models.Campaign.user_id == current_user.id
    ).count()
    
    total_calls = db.query(models.Conversation).filter(
        models.Conversation.user_id == current_user.id
    ).count()
    
    successful_calls = db.query(models.Conversation).filter(
        models.Conversation.user_id == current_user.id,
        models.Conversation.status == "completed"
    ).count()
    
    return {
        "total_agents": total_agents,
        "total_campaigns": total_campaigns,
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "success_rate": (successful_calls / total_calls * 100) if total_calls > 0 else 0
    }

# File ke end mein (existing functions ke neeche) ye function add karo:

@router.get("/test-plivo")
async def test_plivo_connection(
    current_user: models.User = Depends(auth.get_current_active_user_from_cookie)
):
    """Test Plivo connection"""
    try:
        plivo_client = PlivoClient()
        result = plivo_client.verify_credentials()
        
        return {
            "success": result["success"],
            "message": "Plivo connection successful!" if result["success"] else f"Connection failed: {result['error']}",
            "details": result
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Plivo configuration error: {str(e)}"
        }