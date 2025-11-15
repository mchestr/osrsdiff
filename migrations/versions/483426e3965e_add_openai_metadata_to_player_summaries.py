"""Add OpenAI API response metadata to player_summaries table

Revision ID: 483426e3965e
Revises: 0cd763c34e05
Create Date: 2025-01-27 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "483426e3965e"
down_revision: Union[str, Sequence[str], None] = "0cd763c34e05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "player_summaries",
        sa.Column(
            "prompt_tokens",
            sa.Integer(),
            nullable=True,
            comment="Number of tokens used in the prompt",
        ),
    )
    op.add_column(
        "player_summaries",
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=True,
            comment="Number of tokens used in the completion",
        ),
    )
    op.add_column(
        "player_summaries",
        sa.Column(
            "total_tokens",
            sa.Integer(),
            nullable=True,
            comment="Total number of tokens used (prompt + completion)",
        ),
    )
    op.add_column(
        "player_summaries",
        sa.Column(
            "finish_reason",
            sa.String(length=50),
            nullable=True,
            comment="Reason the completion finished (e.g., 'stop', 'length', 'content_filter')",
        ),
    )
    op.add_column(
        "player_summaries",
        sa.Column(
            "response_id",
            sa.String(length=200),
            nullable=True,
            comment="OpenAI API response ID for tracking",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("player_summaries", "response_id")
    op.drop_column("player_summaries", "finish_reason")
    op.drop_column("player_summaries", "total_tokens")
    op.drop_column("player_summaries", "completion_tokens")
    op.drop_column("player_summaries", "prompt_tokens")

