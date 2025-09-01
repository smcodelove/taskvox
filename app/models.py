# FILE: app/models.py
# REPLACE YOUR ENTIRE app/models.py WITH THIS

"""
TasKvox AI - Database Models (White-Label Version)
No ElevenLabs references visible to client
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    voice_api_key = Column(Text, nullable=True)  # CHANGED: White-label field name
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    external_agent_id = Column(String(255), nullable=True)  # CHANGED: White-label field name
    name = Column(String(255), nullable=False)
    voice_id = Column(String(255), nullable=True)
    system_prompt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="agents")
    campaigns = relationship("Campaign", back_populates="agent", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    total_contacts = Column(Integer, default=0)
    completed_calls = Column(Integer, default=0)
    successful_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)
    total_cost = Column(String(50), nullable=True)  # Store as string for precision
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="campaigns")
    agent = relationship("Agent", back_populates="campaigns")
    conversations = relationship("Conversation", back_populates="campaign", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    external_conversation_id = Column(String(255), nullable=True)  # CHANGED: White-label field name
    phone_number = Column(String(20), nullable=True)
    contact_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)  # completed, failed, in_progress
    duration_seconds = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=True)
    cost = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    agent = relationship("Agent", back_populates="conversations")
    campaign = relationship("Campaign", back_populates="conversations")