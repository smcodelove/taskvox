"""Add batch calling support

Revision ID: 5f71525ce6a3
Revises: 002_batch_calling
Create Date: 2025-09-01 13:14:20.750205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f71525ce6a3'
down_revision: Union[str, None] = '002_batch_calling'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
