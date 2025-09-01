# FILE: app/schemas.py
# REPLACE YOUR ENTIRE app/schemas.py WITH THIS

"""
TasKvox AI - Pydantic Schemas (White-Label Version)
No ElevenLabs references visible to client
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    voice_api_key: Optional[str] = None  # CHANGED: White-label field name

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Agent Schemas
class AgentBase(BaseModel):
    name: str
    voice_id: Optional[str] = None
    system_prompt: Optional[str] = None

class AgentCreate(AgentBase):
    pass

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    voice_id: Optional[str] = None
    system_prompt: Optional[str] = None
    is_active: Optional[bool] = None

class Agent(AgentBase):
    id: int
    user_id: int
    external_agent_id: Optional[str] = None  # CHANGED: White-label field name
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Campaign Schemas
class CampaignBase(BaseModel):
    name: str
    agent_id: int

class CampaignCreate(CampaignBase):
    pass

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    total_contacts: Optional[int] = None
    completed_calls: Optional[int] = None
    successful_calls: Optional[int] = None
    failed_calls: Optional[int] = None

class Campaign(CampaignBase):
    id: int
    user_id: int
    status: str
    total_contacts: int
    completed_calls: int
    successful_calls: int
    failed_calls: int
    total_cost: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Conversation Schemas
class ConversationBase(BaseModel):
    phone_number: Optional[str] = None
    contact_name: Optional[str] = None

class ConversationCreate(ConversationBase):
    agent_id: int
    campaign_id: Optional[int] = None

class ConversationUpdate(BaseModel):
    status: Optional[str] = None
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    cost: Optional[str] = None

class Conversation(ConversationBase):
    id: int
    user_id: int
    agent_id: int
    campaign_id: Optional[int] = None
    external_conversation_id: Optional[str] = None  # CHANGED: White-label field name
    status: Optional[str] = None
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    cost: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Dashboard Schemas
class DashboardStats(BaseModel):
    total_agents: int
    total_campaigns: int
    total_conversations: int
    active_campaigns: int
    success_rate: float
    total_cost: str

# File Upload Schemas
class ContactUpload(BaseModel):
    phone_number: str
    name: Optional[str] = None
    
class CampaignLaunch(BaseModel):
    campaign_id: int
    contacts: List[ContactUpload]