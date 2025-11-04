"""Add schedule_id column to players table

Revision ID: a1b2c3d4e5f6
Revises: 23d56873f1dd
Create Date: 2025-11-03 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "23d56873f1dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add schedule_id column to players table
    op.add_column(
        "players",
        sa.Column(
            "schedule_id",
            sa.String(length=255),
            nullable=True,
            comment="TaskIQ schedule ID for this player's fetch task",
        ),
    )

    # Add index for efficient schedule_id lookups
    op.create_index(
        op.f("ix_players_schedule_id"),
        "players",
        ["schedule_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index first
    op.drop_index(op.f("ix_players_schedule_id"), table_name="players")

    # Drop schedule_id column
    op.drop_column("players", "schedule_id")
