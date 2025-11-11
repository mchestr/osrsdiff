"""TaskIQ tasks for OSRS hiscore data fetching and processing."""

# Import fetch tasks from fetch module
from app.workers.fetch import (
    fetch_player_hiscores_task,
)
