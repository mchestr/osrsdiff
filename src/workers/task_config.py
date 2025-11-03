"""Configuration for scheduled tasks."""

from typing import Dict, List

# Scheduled tasks configuration
SCHEDULED_TASKS = [
    {
        "name": "fetch_hiscores",
        "cron_expression": "*/30 * * * *",  # Every 30 minutes
        "task_module": "src.workers.fetch",
        "task_function": "process_scheduled_fetches_task",
        "description": "Fetch hiscore data for all active players",
    },
    {
        "name": "check_game_modes",
        "cron_expression": "0 2 * * *",  # Daily at 2 AM UTC
        "task_module": "src.workers.fetch",
        "task_function": "check_game_mode_downgrades_task",
        "description": "Check all players for game mode downgrades",
    },
]


def get_task_configs() -> List[Dict]:
    """Get the list of scheduled task configurations."""
    return SCHEDULED_TASKS.copy()
