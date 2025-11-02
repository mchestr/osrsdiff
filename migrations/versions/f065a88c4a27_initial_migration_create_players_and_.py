"""Initial migration: create all tables (players, hiscore_records, users)

Revision ID: f065a88c4a27
Revises:
Create Date: 2025-11-02 09:24:43.774757

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f065a88c4a27"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(
        op.f("ix_users_username"), "users", ["username"], unique=True
    )

    # Create players table
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=12), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_fetched", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("fetch_interval_minutes", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_players")),
    )
    op.create_index(
        op.f("ix_players_username"), "players", ["username"], unique=True
    )

    # Create hiscore_records table
    op.create_table(
        "hiscore_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("overall_rank", sa.Integer(), nullable=True),
        sa.Column("overall_level", sa.Integer(), nullable=True),
        sa.Column("overall_experience", sa.Integer(), nullable=True),
        sa.Column("skills_data", sa.JSON(), nullable=False),
        sa.Column("bosses_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["player_id"],
            ["players.id"],
            name=op.f("fk_hiscore_records_player_id_players"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hiscore_records")),
    )
    op.create_index(
        op.f("ix_hiscore_records_fetched_at"),
        "hiscore_records",
        ["fetched_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_hiscore_records_player_id"),
        "hiscore_records",
        ["player_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop hiscore_records table
    op.drop_index(
        op.f("ix_hiscore_records_player_id"), table_name="hiscore_records"
    )
    op.drop_index(
        op.f("ix_hiscore_records_fetched_at"), table_name="hiscore_records"
    )
    op.drop_table("hiscore_records")

    # Drop players table
    op.drop_index(op.f("ix_players_username"), table_name="players")
    op.drop_table("players")

    # Drop users table
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
