"""Add task_executions table for error tracking

Revision ID: 3ada2832d7c7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-27 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3ada2832d7c7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "task_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "task_name",
            sa.String(length=255),
            nullable=False,
            comment="Name of the task function (e.g., 'fetch_player_hiscores_task')",
        ),
        sa.Column(
            "task_args",
            sa.JSON(),
            nullable=True,
            comment="Task arguments as JSON (e.g., {'username': 'player1'})",
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            comment="Execution status (success, failure, retry, etc.)",
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of retry attempts (0 for first attempt)",
        ),
        sa.Column(
            "schedule_id",
            sa.String(length=255),
            nullable=True,
            comment="TaskIQ schedule ID if this was a scheduled task",
        ),
        sa.Column(
            "schedule_type",
            sa.String(length=50),
            nullable=True,
            comment="Type of schedule (e.g., 'player_fetch', 'maintenance')",
        ),
        sa.Column(
            "player_id",
            sa.Integer(),
            nullable=True,
            comment="Player ID if this task is related to a player",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the task execution started",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the task execution completed",
        ),
        sa.Column(
            "duration_seconds",
            sa.Float(),
            nullable=True,
            comment="Task execution duration in seconds",
        ),
        sa.Column(
            "error_type",
            sa.String(length=255),
            nullable=True,
            comment="Type/class name of the error (e.g., 'RateLimitError')",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error message",
        ),
        sa.Column(
            "error_traceback",
            sa.Text(),
            nullable=True,
            comment="Full error traceback for debugging",
        ),
        sa.Column(
            "result_data",
            sa.JSON(),
            nullable=True,
            comment="Task result data as JSON (for successful executions)",
        ),
        sa.Column(
            "execution_metadata",
            sa.JSON(),
            nullable=True,
            comment="Additional execution metadata",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this record was created",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_executions")),
    )

    # Create indexes for efficient queries
    op.create_index(
        op.f("ix_task_executions_task_name"),
        "task_executions",
        ["task_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_executions_status"),
        "task_executions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_executions_schedule_id"),
        "task_executions",
        ["schedule_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_executions_player_id"),
        "task_executions",
        ["player_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_executions_started_at"),
        "task_executions",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_task_executions_created_at"),
        "task_executions",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index(op.f("ix_task_executions_created_at"), table_name="task_executions")
    op.drop_index(op.f("ix_task_executions_started_at"), table_name="task_executions")
    op.drop_index(op.f("ix_task_executions_player_id"), table_name="task_executions")
    op.drop_index(op.f("ix_task_executions_schedule_id"), table_name="task_executions")
    op.drop_index(op.f("ix_task_executions_status"), table_name="task_executions")
    op.drop_index(op.f("ix_task_executions_task_name"), table_name="task_executions")

    # Drop table
    op.drop_table("task_executions")

