"""Add game_mode column to players table

Revision ID: f2a3b4c5d6e7
Revises: 1adcb6c751b1
Create Date: 2025-01-28 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "1adcb6c751b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add game_mode column to players table
    op.add_column(
        "players",
        sa.Column(
            "game_mode",
            sa.String(length=20),
            nullable=True,
            comment="Player game mode (regular, ironman, hardcore, ultimate)",
        ),
    )

    # Add index for efficient game_mode lookups
    op.create_index(
        op.f("ix_players_game_mode"),
        "players",
        ["game_mode"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index first
    op.drop_index(op.f("ix_players_game_mode"), table_name="players")

    # Drop game_mode column
    op.drop_column("players", "game_mode")

