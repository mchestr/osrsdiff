# Design Document

## Overview

This design outlines the refactoring of OSRS Diff's custom task scheduling system to use TaskIQ's native TaskiqScheduler with RedisScheduleSource. The new architecture will replace the current custom cron-based scheduler with TaskIQ's built-in scheduling capabilities, enabling dynamic task management and better integration with the existing task queue system.

The key architectural change is moving from a batch processing model (where one task processes all players) to an individual scheduling model (where each player has their own scheduled task). This provides better granular control and aligns with TaskIQ's scheduler design patterns.

## Architecture

### Current Architecture
```
Custom Scheduler (scheduler.py) 
    ↓ (cron: */30 * * * *)
process_scheduled_fetches_task
    ↓ (queries all active players)
Multiple fetch_player_hiscores_task.kiq() calls
```

### New Architecture
```
TaskiqScheduler + RedisScheduleSource
    ↓ (individual cron schedules per player)
fetch_player_hiscores_task (direct scheduling)
    ↓ (one task per player)
Individual player data fetching
```

### Components Overview

1. **TaskiqScheduler**: Main scheduler instance that manages all scheduled tasks
2. **RedisScheduleSource**: Persistent storage for dynamic schedules in Redis
3. **LabelScheduleSource**: Static schedules defined in task decorators (for game mode checks)
4. **Player Schedule Manager**: Service layer for managing individual player schedules
5. **Migration Service**: Handles transition from old to new scheduler

## Components and Interfaces

### TaskiqScheduler Configuration

```python
from taskiq import TaskiqScheduler
from taskiq_redis import RedisScheduleSource
from taskiq.schedule_sources import LabelScheduleSource

# Redis-based schedule source for dynamic scheduling
redis_schedule_source = RedisScheduleSource(
    redis_url=settings.redis.url,
    prefix="osrsdiff:schedules"
)

# Label-based source for static schedules (game mode checks)
label_schedule_source = LabelScheduleSource(broker)

# Main scheduler with multiple sources
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[redis_schedule_source, label_schedule_source]
)
```

### Player Schedule Manager Service

```python
class PlayerScheduleManager:
    """Manages individual player scheduling using TaskIQ scheduler."""
    
    def __init__(self, redis_source: RedisScheduleSource):
        self.redis_source = redis_source
    
    async def schedule_player(self, player: Player) -> str:
        """Create a scheduled task for a player."""
        cron_expression = self._interval_to_cron(player.fetch_interval_minutes)
        
        # Use deterministic schedule ID based on player ID to avoid duplicates
        # and enable easy lookup/management
        custom_schedule_id = f"player_fetch_{player.id}"
        
        schedule = await fetch_player_hiscores_task.kicker().with_schedule_id(
            custom_schedule_id
        ).with_labels(
            player_id=str(player.id),
            schedule_type="player_fetch"
        ).schedule_by_cron(
            self.redis_source,
            cron_expression,
            player.username
        )
        
        # Store schedule_id in player record
        player.schedule_id = schedule.schedule_id
        return schedule.schedule_id
    
    async def unschedule_player(self, player: Player) -> None:
        """Remove a player's scheduled task."""
        if player.schedule_id:
            try:
                await self.redis_source.delete_schedule(player.schedule_id)
            except Exception as e:
                logger.warning(f"Failed to delete schedule {player.schedule_id}: {e}")
            finally:
                player.schedule_id = None
    
    async def reschedule_player(self, player: Player) -> str:
        """Update a player's schedule (unschedule + schedule)."""
        await self.unschedule_player(player)
        return await self.schedule_player(player)
    
    async def ensure_player_scheduled(self, player: Player) -> str:
        """Ensure player has a valid schedule, create if missing."""
        if not player.schedule_id:
            return await self.schedule_player(player)
        
        # Verify schedule still exists in Redis
        try:
            schedules = await self.redis_source.get_schedules()
            schedule_ids = {s.schedule_id for s in schedules}
            
            if player.schedule_id not in schedule_ids:
                logger.warning(f"Schedule {player.schedule_id} not found in Redis, recreating")
                return await self.schedule_player(player)
        except Exception as e:
            logger.error(f"Failed to verify schedule existence: {e}")
            # Recreate schedule to be safe
            return await self.schedule_player(player)
        
        return player.schedule_id
    
    def _interval_to_cron(self, minutes: int) -> str:
        """Convert fetch interval to cron expression."""
        if minutes < 60:
            return f"*/{minutes} * * * *"
        elif minutes == 60:
            return "0 * * * *"  # Every hour
        elif minutes == 1440:
            return "0 0 * * *"  # Daily
        else:
            # For other intervals, use minute-based cron
            return f"*/{minutes} * * * *"
```

### Updated Player Model

```python
class Player(Base):
    # ... existing fields ...
    
    # New field to track TaskIQ schedule ID
    schedule_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True,
        comment="TaskIQ schedule ID for this player's fetch task"
    )
```

### Game Mode Check Task (Static Schedule)

```python
# Use LabelScheduleSource for static schedules
@broker.task(schedule=[{"cron": "0 2 * * *"}])  # Daily at 2 AM UTC
async def check_game_mode_downgrades_task() -> Dict[str, Any]:
    """Check all players for game mode downgrades."""
    # Existing implementation remains the same
    return await _check_game_mode_downgrades()
```

### Updated Worker Startup

```python
@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(context: TaskiqState) -> None:
    """Initialize worker resources on startup."""
    print("TaskIQ worker starting up...")
    
    # Initialize database connection pool
    from src.models.base import init_db
    await init_db()
    
    # Note: TaskiqScheduler is run separately via CLI
    # No need to start custom scheduler here
    
    print("TaskIQ worker startup complete")
```

## Data Models

### Database Schema Changes

```sql
-- Add schedule_id column to players table
ALTER TABLE players 
ADD COLUMN schedule_id VARCHAR(255) NULL 
COMMENT 'TaskIQ schedule ID for this player fetch task (format: player_fetch_{player_id})';

-- Index for efficient schedule lookups
CREATE INDEX idx_players_schedule_id ON players(schedule_id) 
WHERE schedule_id IS NOT NULL;
```

### Schedule ID Strategy

To address schedule ID stability and management concerns:

1. **Deterministic Schedule IDs**: Use format `player_fetch_{player_id}` for predictable IDs
2. **Labels for Metadata**: Store player_id and schedule_type in TaskIQ labels for querying
3. **Verification Logic**: Check schedule existence in Redis and recreate if missing
4. **Graceful Degradation**: Handle missing schedules without breaking the system

### Schedule Metadata and Labels

TaskIQ labels are key-value metadata attached to tasks and schedules. They serve multiple purposes:

- **Task Identification**: Store metadata like player_id for easy identification
- **Context Access**: Available during task execution via `context.message.labels.get("key")`
- **Filtering/Routing**: Can be used by middlewares for task routing or filtering
- **System Tracking**: TaskIQ uses internal labels for requeue counting and other features

TaskIQ's RedisScheduleSource stores schedule metadata in Redis with the following structure:

```json
{
  "schedule_id": "player_fetch_123",
  "task_name": "fetch_player_hiscores_task", 
  "cron": "*/30 * * * *",
  "args": ["player_username"],
  "kwargs": {},
  "labels": {
    "player_id": "123",
    "schedule_type": "player_fetch"
  }
}
```

**Label Usage in Tasks:**
```python
@broker.task
async def fetch_player_hiscores_task(username: str, context: Context = TaskiqDepends()) -> Dict[str, Any]:
    # Access schedule metadata from labels
    player_id = context.message.labels.get("player_id")
    schedule_type = context.message.labels.get("schedule_type")
    schedule_id = context.message.labels.get("schedule_id")
    
    logger.info(f"Fetching hiscores for player {player_id} (schedule: {schedule_id})")
    # ... existing fetch logic
```

### Schedule ID Lifecycle

1. **Creation**: Generate deterministic ID `player_fetch_{player_id}`
2. **Storage**: Store in both database (player.schedule_id) and Redis (schedule metadata)
3. **Verification**: Periodically verify schedule exists in Redis
4. **Recovery**: Recreate missing schedules automatically
5. **Cleanup**: Remove schedules when players are deleted

## Error Handling

### Schedule Management Errors

1. **Redis Connection Failures**: Graceful degradation with logging and retry logic
2. **Duplicate Scheduling**: Use deterministic schedule IDs to prevent duplicates
3. **Orphaned Schedules**: Cleanup utility to remove schedules for deleted players
4. **Schedule Conflicts**: Deterministic IDs prevent multiple schedules for same player
5. **Missing Schedules**: Automatic recreation when schedule_id exists but Redis schedule doesn't

### Schedule ID Stability Issues

1. **Schedule Not Found**: If schedule_id exists in DB but not in Redis, recreate automatically
2. **Inconsistent State**: Regular verification job to ensure DB and Redis are in sync
3. **Migration Failures**: Rollback mechanism to restore old scheduler if needed
4. **Redis Data Loss**: Recovery process to recreate all schedules from active players

### Migration Error Handling

1. **Partial Migration Failures**: Track migration progress and allow resumption
2. **Schedule Creation Failures**: Log failures and provide manual retry mechanisms  
3. **Data Consistency**: Verification utilities to ensure player.schedule_id matches Redis
4. **Rollback Support**: Ability to revert to old scheduler if migration fails

## Testing Strategy

### Unit Tests

1. **PlayerScheduleManager Tests**:
   - Test schedule creation, deletion, and updates
   - Test cron expression generation for various intervals
   - Mock RedisScheduleSource for isolated testing

2. **Interval to Cron Conversion Tests**:
   - Test common intervals (30 min, 1 hour, daily)
   - Test edge cases and invalid intervals
   - Verify cron expression accuracy

### Integration Tests

1. **End-to-End Schedule Tests**:
   - Create player → verify schedule created in Redis
   - Update player interval → verify schedule updated
   - Delete player → verify schedule removed

2. **TaskiqScheduler Integration**:
   - Test scheduler startup with multiple sources
   - Verify task execution from scheduled tasks
   - Test scheduler shutdown and cleanup

### Migration Tests

1. **Data Migration Tests**:
   - Test migration from old scheduler to new scheduler
   - Verify all active players get scheduled
   - Test rollback scenarios

2. **Performance Tests**:
   - Test scheduler performance with large numbers of players
   - Verify Redis performance under load
   - Test memory usage and cleanup

## Deployment Strategy

### Phase 1: Preparation
1. Deploy database schema changes (add schedule_id column)
2. Deploy new TaskiqScheduler code without activating
3. Install taskiq CLI dependencies

### Phase 2: Migration
1. Run migration script to create schedules for existing players
2. Update player records with schedule_id values
3. Verify all schedules created successfully

### Phase 3: Cutover
1. Stop old custom scheduler
2. Start TaskiqScheduler using `taskiq scheduler src.workers.main:scheduler`
3. Monitor task execution and Redis schedule storage

### Phase 4: Cleanup
1. Remove old scheduler code after successful operation
2. Remove old scheduled task configurations
3. Update documentation and deployment scripts

## Configuration Changes

### Environment Variables

```bash
# TaskIQ Scheduler Configuration
TASKIQ_SCHEDULER_REDIS_URL=redis://localhost:6379/0
TASKIQ_SCHEDULER_PREFIX=osrsdiff:schedules

# CLI Command for Scheduler
TASKIQ_SCHEDULER_COMMAND="taskiq scheduler src.workers.main:scheduler"
```

### Docker Compose Updates

```yaml
services:
  scheduler:
    build: .
    command: taskiq scheduler src.workers.main:scheduler
    environment:
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
```

## Monitoring and Observability

### Metrics to Track

1. **Schedule Management**:
   - Number of active schedules
   - Schedule creation/deletion rates
   - Failed schedule operations

2. **Task Execution**:
   - Individual player fetch success rates
   - Task execution timing per player
   - Redis schedule source performance

3. **System Health**:
   - TaskiqScheduler uptime and restarts
   - Redis connection health
   - Schedule consistency checks

### Logging Enhancements

1. **Schedule Operations**: Log all schedule create/update/delete operations
2. **Task Context**: Include schedule_id in task execution logs
3. **Error Tracking**: Enhanced error logging for schedule-related failures

This design provides a comprehensive migration path from the custom scheduler to TaskIQ's native scheduling system while maintaining all existing functionality and adding dynamic scheduling capabilities.