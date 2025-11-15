"""Preserve player summaries when players are deleted

Revision ID: e1f2a3b4c5d6
Revises: 483426e3965e
Create Date: 2025-01-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "483426e3965e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the existing foreign key constraint
    op.drop_constraint(
        "fk_player_summaries_player_id_players",
        "player_summaries",
        type_="foreignkey",
    )

    # Alter the column to be nullable
    op.alter_column(
        "player_summaries",
        "player_id",
        nullable=True,
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    # Recreate the foreign key constraint with SET NULL on delete
    op.create_foreign_key(
        "fk_player_summaries_player_id_players",
        "player_summaries",
        "players",
        ["player_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the foreign key constraint
    op.drop_constraint(
        "fk_player_summaries_player_id_players",
        "player_summaries",
        type_="foreignkey",
    )

    # Delete any summaries with null player_id (orphaned summaries)
    op.execute("DELETE FROM player_summaries WHERE player_id IS NULL")

    # Alter the column to be non-nullable
    op.alter_column(
        "player_summaries",
        "player_id",
        nullable=False,
        existing_type=sa.Integer(),
        existing_nullable=True,
    )

    # Recreate the foreign key constraint with CASCADE on delete
    op.create_foreign_key(
        "fk_player_summaries_player_id_players",
        "player_summaries",
        "players",
        ["player_id"],
        ["id"],
        ondelete="CASCADE",
    )

