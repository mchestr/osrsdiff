"""merge settings and player summaries branches

Revision ID: 1adcb6c751b1
Revises: d0e1f2a3b4c5, e1f2a3b4c5d6
Create Date: 2025-11-15 14:31:09.651797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1adcb6c751b1'
down_revision: Union[str, Sequence[str], None] = ('d0e1f2a3b4c5', 'e1f2a3b4c5d6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
