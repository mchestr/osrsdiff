"""Add player_summaries table for AI-generated progress summaries

Revision ID: 0cd763c34e05
Revises: 3ada2832d7c7
Create Date: 2025-01-27 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0cd763c34e05"
down_revision: Union[str, Sequence[str], None] = "3ada2832d7c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "player_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "player_id",
            sa.Integer(),
            nullable=False,
            comment="Reference to the player this summary belongs to",
        ),
        sa.Column(
            "period_start",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Start of the period covered by this summary",
        ),
        sa.Column(
            "period_end",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="End of the period covered by this summary",
        ),
        sa.Column(
            "summary_text",
            sa.Text(),
            nullable=False,
            comment="AI-generated summary text",
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this summary was generated",
        ),
        sa.Column(
            "model_used",
            sa.String(length=100),
            nullable=True,
            comment="OpenAI model used for generation (e.g., 'gpt-4', 'gpt-3.5-turbo')",
        ),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name=op.f("fk_player_summaries_player_id_players"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_player_summaries")),
    )

    # Create indexes for efficient queries
    op.create_index(
        op.f("ix_player_summaries_player_id"),
        "player_summaries",
        ["player_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_player_summaries_period_start"),
        "player_summaries",
        ["period_start"],
        unique=False,
    )
    op.create_index(
        op.f("ix_player_summaries_period_end"),
        "player_summaries",
        ["period_end"],
        unique=False,
    )
    op.create_index(
        op.f("ix_player_summaries_generated_at"),
        "player_summaries",
        ["generated_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index(
        op.f("ix_player_summaries_generated_at"), table_name="player_summaries"
    )
    op.drop_index(
        op.f("ix_player_summaries_period_end"), table_name="player_summaries"
    )
    op.drop_index(
        op.f("ix_player_summaries_period_start"), table_name="player_summaries"
    )
    op.drop_index(
        op.f("ix_player_summaries_player_id"), table_name="player_summaries"
    )

    # Drop table
    op.drop_table("player_summaries")

