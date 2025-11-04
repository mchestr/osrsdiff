# TaskIQ Scheduler Configuration

This document describes the TaskIQ scheduler configuration and usage in the OSRS Diff application.

## Overview

The application uses TaskIQ's native `TaskiqScheduler` with multiple schedule sources:

1. **RedisScheduleSource**: For dynamic scheduling of individual player fetch tasks
2. **LabelScheduleSource**: For static schedules defined in task decorators (e.g., daily game mode checks)

## Configuration

### Environment Variables

The scheduler uses the following environment variables:

```bash
# Redis connection for schedule storage
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10

# TaskIQ scheduler settings
TASKIQ_SCHEDULER_PREFIX=osrsdiff:schedules
```

### Scheduler Sources

#### RedisScheduleSource
- Stores dynamic schedules in Redis
- Used for individual player fetch tasks
- Supports runtime schedule creation/modification/deletion
- Prefix: `osrsdiff:schedules`

#### LabelScheduleSource
- Reads schedules from task decorators
- Used for static schedules like daily game mode checks
- Configured directly in task code with `schedule=[{"cron": "..."}]`

## Running the Scheduler

### Using Docker Compose

The scheduler runs as a separate service in Docker:

```bash
# Start all services including scheduler
docker-compose up -d

# View scheduler logs
docker-compose logs -f scheduler
```

### Using TaskIQ CLI

Run the scheduler directly using TaskIQ CLI:

```bash
# Run scheduler
taskiq scheduler src.workers.main:scheduler

# Run with specific log level
PYTHONPATH=. taskiq scheduler src.workers.main:scheduler --log-level INFO
```

### Using Python Script

Use the provided script for development:

```bash
python scripts/run_scheduler.py
```

## Schedule Management

### Dynamic Schedules (Player Fetches)

Individual player schedules are managed through the `PlayerScheduleManager`:

```python
from src.services.scheduler import get_player_schedule_manager

# Get the schedule manager
schedule_manager = await get_player_schedule_manager()

# Schedule a player
schedule_id = await schedule_manager.schedule_player(player)

# Reschedule a player (change interval)
schedule_id = await schedule_manager.reschedule_player(player)

# Unschedule a player
await schedule_manager.unschedule_player(player)
```

### Static Schedules (System Tasks)

Static schedules are defined in task decorators:

```python
@broker.task(schedule=[{"cron": "0 2 * * *"}])  # Daily at 2 AM UTC
async def check_game_mode_downgrades_task():
    # Task implementation
    pass
```

## Monitoring

### Schedule Status

Check schedule status through the API:

```bash
# List all scheduled tasks
GET /api/system/scheduled-tasks

# Trigger a task manually
POST /api/system/trigger-task/check_game_mode_downgrades_task
```

### Redis Inspection

View schedules directly in Redis:

```bash
# Connect to Redis
redis-cli

# List all schedule keys
KEYS osrsdiff:schedules:*

# View a specific schedule
GET osrsdiff:schedules:player_fetch_123
```

## Troubleshooting

### Common Issues

1. **Scheduler not starting**: Check Redis connection and configuration
2. **Schedules not executing**: Verify worker is running and connected to same Redis
3. **Duplicate schedules**: Use deterministic schedule IDs to prevent duplicates

### Logs

Check scheduler logs for debugging:

```bash
# Docker logs
docker-compose logs -f scheduler

# Application logs
tail -f logs/scheduler.log
```

### Recovery

If schedules are lost or corrupted:

1. Stop the scheduler
2. Clear Redis schedule data: `redis-cli FLUSHDB`
3. Run migration script to recreate schedules: `python scripts/migrate_to_taskiq_scheduler.py`
4. Restart the scheduler

## Migration from Old Scheduler

The application has been migrated from a custom cron-based scheduler to TaskIQ's native scheduler. The migration includes:

1. **Removed**: Custom scheduler code (`src/workers/scheduler.py`)
2. **Added**: TaskIQ scheduler configuration
3. **Updated**: Docker Compose with scheduler service
4. **Migrated**: Individual player schedules to Redis

See `scripts/migrate_to_taskiq_scheduler.py` for the migration process.