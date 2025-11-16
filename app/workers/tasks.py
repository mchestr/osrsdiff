"""TaskIQ tasks for OSRS hiscore data fetching and processing."""

# Import fetch tasks from fetch module
from app.workers.fetch import (
    fetch_player_hiscores_task,
)
from app.workers.maintenance import schedule_maintenance_job

# Import summary tasks from summaries module
from app.workers.summaries import (
    daily_summary_generation_job,
    generate_player_summary_task,
)
