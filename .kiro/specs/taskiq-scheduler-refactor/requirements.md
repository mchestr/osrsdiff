# Requirements Document

## Introduction

This specification defines the requirements for refactoring the OSRS Diff application's current custom task scheduling system to use TaskIQ's native TaskiqScheduler with RedisScheduleSource for dynamic scheduling capabilities. The current system uses a custom cron-based scheduler with Redis locks for leader election, but we want to leverage TaskIQ's built-in scheduling features for better integration, maintainability, and dynamic task management.

## Glossary

- **TaskIQ**: The async distributed task queue library used by the application
- **TaskiqScheduler**: TaskIQ's native scheduler class that manages scheduled task execution
- **RedisScheduleSource**: TaskIQ's Redis-based schedule source that supports dynamic scheduling
- **LabelScheduleSource**: TaskIQ's schedule source that reads schedules from task labels
- **Dynamic Scheduling**: The ability to create, modify, and cancel scheduled tasks at runtime using schedule_by_time() and schedule_by_cron() methods
- **CreatedSchedule**: TaskIQ's object returned when creating schedules, containing schedule_id and unschedule() method
- **Custom Scheduler**: The current cron-based scheduling implementation in `src/workers/scheduler.py`
- **Hiscore Fetch Task**: Background task that fetches OSRS player data from the API
- **Game Mode Check Task**: Daily task that checks for player game mode downgrades
- **Player Management Service**: Service layer that manages player tracking settings
- **Schedule Source**: TaskIQ's abstraction for storing and retrieving scheduled tasks

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want to use TaskIQ's native TaskiqScheduler instead of the custom scheduler, so that I have better integration with the task queue system and reduced maintenance overhead.

#### Acceptance Criteria

1. WHEN the application starts, THE TaskiqScheduler SHALL replace the custom scheduler implementation
2. WHEN the scheduler runs, THE TaskiqScheduler SHALL use RedisScheduleSource for dynamic scheduling capabilities
3. WHEN the system shuts down, THE TaskiqScheduler SHALL properly clean up scheduled tasks
4. THE Application SHALL remove all custom scheduler code from `src/workers/scheduler.py`
5. THE Application SHALL use the `taskiq scheduler` CLI command to run the scheduler process

### Requirement 2

**User Story:** As a developer, I want dynamic scheduling capabilities, so that I can create, modify, and cancel scheduled tasks at runtime without restarting the application.

#### Acceptance Criteria

1. WHEN a new player is added for tracking, THE System SHALL use schedule_by_cron() to create a scheduled fetch task
2. WHEN a player's fetch interval is modified, THE System SHALL unschedule the existing task and create a new one
3. WHEN a player is deactivated or removed, THE System SHALL call unschedule() on the CreatedSchedule object
4. THE System SHALL store schedule_id values to track and manage individual player schedules
5. THE System SHALL use RedisScheduleSource for persistent schedule storage across restarts

### Requirement 3

**User Story:** As a system operator, I want to track and manage scheduled tasks, so that I can monitor task execution and troubleshoot scheduling issues.

#### Acceptance Criteria

1. THE System SHALL store schedule_id values in the Player model to track individual schedules
2. WHEN queried, THE System SHALL provide information about active scheduled tasks using stored schedule_id values
3. THE System SHALL allow manual triggering of tasks using the existing task.kiq() method
4. THE System SHALL access schedule_id from task context using context.message.labels.get("schedule_id")
5. THE System SHALL prevent duplicate scheduling by checking existing schedule_id before creating new schedules

### Requirement 4

**User Story:** As a player data consumer, I want the same reliable hiscore fetching behavior, so that player data continues to be updated according to individual fetch intervals.

#### Acceptance Criteria

1. WHEN using TaskiqScheduler, THE System SHALL convert player fetch_interval_minutes to cron expressions
2. THE System SHALL create individual scheduled tasks for each player instead of batch processing
3. THE System SHALL maintain the same error handling and retry logic for failed fetches
4. THE System SHALL preserve the existing fetch_player_hiscores_task functionality
5. THE System SHALL migrate existing players to individual scheduled tasks during deployment

### Requirement 5

**User Story:** As a system administrator, I want improved task management capabilities, so that I can better control and monitor the scheduling system.

#### Acceptance Criteria

1. THE System SHALL provide API endpoints to list all players with their schedule_id values
2. THE System SHALL allow pausing individual players by unscheduling their tasks
3. THE System SHALL allow resuming individual players by recreating their scheduled tasks
4. THE System SHALL maintain the existing game mode check task using LabelScheduleSource with cron schedule
5. THE System SHALL provide migration utilities to transition from the old scheduler to TaskiqScheduler