# TaskIQ Scheduler Migration and Maintenance

This directory contains utilities for migrating from the custom scheduler to TaskIQ's native scheduler and maintaining schedule health.

## Migration Script

### `migrate_to_taskiq_scheduler.py`

Migrates all existing active players from the custom scheduler to individual TaskIQ schedules.

#### Usage

```bash
# Dry run to see what would be migrated
python scripts/migrate_to_taskiq_scheduler.py --dry-run

# Verify existing schedules only
python scripts/migrate_to_taskiq_scheduler.py --verify-only

# Run actual migration
python scripts/migrate_to_taskiq_scheduler.py

# Resume migration from a specific player ID
python scripts/migrate_to_taskiq_scheduler.py --continue-from 100

# Process in smaller batches
python scripts/migrate_to_taskiq_scheduler.py --batch-size 25
```

#### Features

- **Progress Tracking**: Shows migration progress with detailed statistics
- **Error Handling**: Handles partial failures and allows resumption
- **Verification**: Ensures all players are properly scheduled after migration
- **Batch Processing**: Processes players in configurable batches to avoid overwhelming Redis
- **Logging**: Creates detailed log files for troubleshooting

## Maintenance Script

### `schedule_maintenance.py`

Provides various maintenance operations for schedule health and consistency.

#### Commands

```bash
# List all schedules with their status
python scripts/schedule_maintenance.py list-schedules

# Clean up orphaned schedules (dry run first)
python scripts/schedule_maintenance.py cleanup-orphaned --dry-run
python scripts/schedule_maintenance.py cleanup-orphaned

# Verify schedule consistency between database and Redis
python scripts/schedule_maintenance.py verify-consistency

# Reschedule all players (useful after configuration changes)
python scripts/schedule_maintenance.py bulk-reschedule --dry-run
python scripts/schedule_maintenance.py bulk-reschedule

# Remove a specific schedule
python scripts/schedule_maintenance.py remove-schedule --schedule-id player_fetch_123

# Recreate a specific player's schedule
python scripts/schedule_maintenance.py recreate-schedule --player-id 123
```

#### Options

- `--dry-run`: Show what would be done without making changes
- `--force`: Skip confirmation prompts
- `--batch-size N`: Process items in batches of N (default: 50)

## Background Tasks

### Automatic Maintenance

The system includes background tasks for automatic schedule maintenance:

- **Daily Verification Job**: Runs at 3 AM UTC to verify schedule consistency
- **Automatic Cleanup**: Removes orphaned schedules and fixes missing ones
- **Manual Triggers**: API endpoints to manually trigger maintenance operations

## Migration Process

### Recommended Migration Steps

1. **Preparation**
   ```bash
   # Verify current state
   python scripts/schedule_maintenance.py list-schedules
   
   # Run migration dry run
   python scripts/migrate_to_taskiq_scheduler.py --dry-run
   ```

2. **Migration**
   ```bash
   # Run actual migration
   python scripts/migrate_to_taskiq_scheduler.py
   ```

3. **Verification**
   ```bash
   # Verify migration completeness
   python scripts/migrate_to_taskiq_scheduler.py --verify-only
   
   # Check for any inconsistencies
   python scripts/schedule_maintenance.py verify-consistency
   ```

4. **Cleanup**
   ```bash
   # Clean up any orphaned schedules
   python scripts/schedule_maintenance.py cleanup-orphaned
   ```

### Troubleshooting

#### Common Issues

1. **Redis Connection Errors**
   - Ensure Redis is running and accessible
   - Check Redis URL configuration in environment variables

2. **Database Connection Errors**
   - Ensure PostgreSQL is running and accessible
   - Verify database connection string

3. **Partial Migration Failures**
   - Use `--continue-from` option to resume from last successful player ID
   - Check log files for specific error details

4. **Schedule Inconsistencies**
   - Run `verify-consistency` to identify issues
   - Use `recreate-schedule` for specific problematic players
   - Use `bulk-reschedule` to recreate all schedules if needed

#### Recovery Procedures

1. **If migration fails partway through:**
   ```bash
   # Check what was completed
   python scripts/migrate_to_taskiq_scheduler.py --verify-only
   
   # Resume from last successful player
   python scripts/migrate_to_taskiq_scheduler.py --continue-from <last_player_id>
   ```

2. **If schedules become inconsistent:**
   ```bash
   # Identify issues
   python scripts/schedule_maintenance.py verify-consistency
   
   # Clean up orphaned schedules
   python scripts/schedule_maintenance.py cleanup-orphaned
   
   # Recreate all schedules if needed
   python scripts/schedule_maintenance.py bulk-reschedule
   ```

## Service Integration

### Programmatic Access

The maintenance utilities are also available as services for integration with API endpoints:

```python
from src.services.schedule_maintenance import ScheduleMaintenanceService
from src.services.scheduler import player_schedule_manager

# Create maintenance service
maintenance_service = ScheduleMaintenanceService(player_schedule_manager)

# Use in API endpoints or other services
cleanup_result = await maintenance_service.cleanup_orphaned_schedules(db_session)
consistency_result = await maintenance_service.verify_schedule_consistency(db_session)
```

### Background Task Integration

```python
from src.workers.schedule_maintenance import trigger_schedule_verification, trigger_orphaned_cleanup

# Manually trigger maintenance tasks
verification_result = await trigger_schedule_verification()
cleanup_result = await trigger_orphaned_cleanup()
```

## Monitoring

### Log Files

All operations create detailed log files with timestamps:
- `migration_YYYYMMDD_HHMMSS.log` - Migration operations
- `schedule_maintenance_YYYYMMDD_HHMMSS.log` - Maintenance operations

### Key Metrics to Monitor

- **Schedule Coverage**: Percentage of active players with valid schedules
- **Orphaned Schedules**: Number of Redis schedules without corresponding active players
- **Consistency Issues**: Mismatches between database and Redis
- **Migration Progress**: Number of players successfully migrated

### Health Checks

Regular health checks should include:
1. Verifying all active players have schedule_id values
2. Confirming all schedule_ids exist in Redis
3. Checking for orphaned schedules in Redis
4. Validating schedule configurations match player intervals