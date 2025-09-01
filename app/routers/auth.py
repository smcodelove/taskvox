# FILE: app/routers/auth.py
# REPLACE YOUR ENTIRE app/routers/auth.py WITH THIS

"""
TasKvox AI - Authentication Router (White-Label Version)
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse(
        "login.html", 
        {"request": request, "title": "Login - TasKvox AI"}
    )

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Register page"""
    return templates.TemplateResponse(
        "register.html", 
        {"request": request, "title": "Register - TasKvox AI"}
    )

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint for API access"""
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login")
async def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Login form submission"""
    user = auth.authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "title": "Login - TasKvox AI",
                "error": "Invalid email or password"
            }
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Redirect to dashboard
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True
    )
    return response

@router.post("/register")
async def register_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Register form submission"""
    # Validate passwords match
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "title": "Register - TasKvox AI",
                "error": "Passwords do not match"
            }
        )
    
    # Validate password strength
    if len(password) < 6:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "title": "Register - TasKvox AI",
                "error": "Password must be at least 6 characters long"
            }
        )
    
    try:
        # Create user
        user_data = schemas.UserCreate(email=email, password=password)
        user = auth.create_user(db, user_data)
        
        # Auto-login after registration
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key="access_token", 
            value=f"Bearer {access_token}",
            max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=True
        )
        return response
        
    except HTTPException as e:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "title": "Register - TasKvox AI",
                "error": e.detail
            }
        )

@router.post("/register-api", response_model=schemas.User)
async def register_user_api(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """Register new user via API"""
    return auth.create_user(db, user)

@router.get("/logout")
async def logout():
    """Logout endpoint"""
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response

@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    """Get current user info"""
    return current_user

@router.put("/me", response_model=schemas.User)
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user (white-label)"""
    if user_update.email:
        current_user.email = user_update.email
    if user_update.voice_api_key:  # CHANGED: White-label field
        current_user.voice_api_key = user_update.voice_api_key
    
    db.commit()
    db.refresh(current_user)
    return current_user