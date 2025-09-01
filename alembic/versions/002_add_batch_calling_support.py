"""Add batch calling support

Revision ID: 002_batch_calling
Revises: 517fddc86550
Create Date: 2025-09-01 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_batch_calling'
down_revision: Union[str, None] = '517fddc86550'  # Update this to your latest revision
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Add batch calling support columns and tables"""
    
    # Add new columns to campaigns table
    op.add_column('campaigns', sa.Column('elevenlabs_batch_id', sa.String(255), nullable=True))
    op.add_column('campaigns', sa.Column('batch_status', sa.String(50), nullable=True))
    op.add_column('campaigns', sa.Column('max_concurrent_calls', sa.Integer(), nullable=True, server_default='10'))
    op.add_column('campaigns', sa.Column('retry_attempts', sa.Integer(), nullable=True, server_default='2'))
    
    # Add new columns to conversations table for better tracking
    op.add_column('conversations', sa.Column('call_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conversations', sa.Column('call_ended_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conversations', sa.Column('call_duration_seconds', sa.Integer(), nullable=True))
    op.add_column('conversations', sa.Column('call_cost_cents', sa.Integer(), nullable=True))
    op.add_column('conversations', sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('conversations', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('conversations', sa.Column('metadata', sa.JSON(), nullable=True))
    
    # Add indexes for better performance
    op.create_index('idx_campaigns_batch_id', 'campaigns', ['elevenlabs_batch_id'])
    op.create_index('idx_campaigns_status', 'campaigns', ['status'])
    op.create_index('idx_campaigns_user_status', 'campaigns', ['user_id', 'status'])
    op.create_index('idx_conversations_status', 'conversations', ['status'])
    op.create_index('idx_conversations_campaign_id', 'conversations', ['campaign_id'])
    op.create_index('idx_conversations_created_at', 'conversations', ['created_at'])
    op.create_index('idx_conversations_user_status', 'conversations', ['user_id', 'status'])
    
    # Create campaign_analytics table for detailed tracking
    op.create_table('campaign_analytics',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('calls_attempted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('calls_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('calls_successful', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('calls_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_duration_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cost_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True)
    )
    
    # Add indexes for campaign_analytics
    op.create_index('idx_campaign_analytics_campaign_date', 'campaign_analytics', ['campaign_id', 'date'], unique=True)
    op.create_index('idx_campaign_analytics_date', 'campaign_analytics', ['date'])

def downgrade() -> None:
    """Remove batch calling support"""
    
    # Drop campaign_analytics table
    op.drop_table('campaign_analytics')
    
    # Drop indexes from conversations
    op.drop_index('idx_conversations_user_status')
    op.drop_index('idx_conversations_created_at')
    op.drop_index('idx_conversations_campaign_id') 
    op.drop_index('idx_conversations_status')
    
    # Drop indexes from campaigns
    op.drop_index('idx_campaigns_user_status')
    op.drop_index('idx_campaigns_status')
    op.drop_index('idx_campaigns_batch_id')
    
    # Remove added columns from conversations
    op.drop_column('conversations', 'metadata')
    op.drop_column('conversations', 'error_message')
    op.drop_column('conversations', 'retry_count')
    op.drop_column('conversations', 'call_cost_cents')
    op.drop_column('conversations', 'call_duration_seconds')
    op.drop_column('conversations', 'call_ended_at')
    op.drop_column('conversations', 'call_started_at')
    
    # Remove added columns from campaigns
    op.drop_column('campaigns', 'retry_attempts')
    op.drop_column('campaigns', 'max_concurrent_calls')
    op.drop_column('campaigns', 'batch_status')
    op.drop_column('campaigns', 'elevenlabs_batch_id')