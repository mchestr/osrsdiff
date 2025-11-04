# Implementation Plan

- [x] 1. Set up TaskIQ scheduler infrastructure





  - Create TaskiqScheduler instance with RedisScheduleSource and LabelScheduleSource
  - Configure scheduler with proper Redis connection and settings
  - Update broker configuration to support scheduler components
  - _Requirements: 1.1, 1.2, 1.5_

- [x] 2. Add database schema changes for schedule tracking





  - Create Alembic migration to add schedule_id column to players table
  - Add database index for efficient schedule_id lookups
  - Update Player model to include schedule_id field with proper typing
  - _Requirements: 3.1, 3.5_

- [ ] 3. Implement PlayerScheduleManager service
- [x] 3.1 Create core PlayerScheduleManager class with Redis integration





  - Implement schedule_player() method with deterministic schedule IDs
  - Implement unschedule_player() method with error handling
  - Implement reschedule_player() method for interval updates
  - _Requirements: 2.1, 2.2, 2.3_
- [x] 3.2 Add schedule verification and recovery logic









- [ ] 3.2 Add schedule verification and recovery logic

  - Implement ensure_player_scheduled() method to verify schedule existence
  - Add automatic schedule recreation when Redis schedule is missing
  - Implement interval-to-cron conversion with proper validation
  - _Requirements: 3.3, 4.5, 5.5_


- [x] 4. Update task definitions for scheduler integration




- [x] 4.1 Modify fetch_player_hiscores_task to use labels and context


  - Update task to access player_id and schedule_id from context labels
  - Add logging for schedule metadata in task execution
  - Ensure task maintains existing functionality and error handling
  - _Requirements: 4.3, 4.4_

- [x] 4.2 Convert game mode check task to use LabelScheduleSource


  - Update check_game_mode_downgrades_task with schedule decorator
  - Remove task from old scheduler configuration
  - Verify daily execution timing remains consistent
  - _Requirements: 1.1, 4.4, 5.4_
- [x] 5. Create migration utilities and services




- [ ] 5. Create migration utilities and services

- [x] 5.1 Implement migration script for existing players


  - Create script to migrate all active players to individual schedules
  - Add progress tracking and error handling for partial failures
  - Implement verification to ensure all players are properly scheduled
  - _Requirements: 4.5, 5.5_

- [x] 5.2 Add schedule cleanup and maintenance utilities


  - Create utility to remove orphaned schedules for deleted players
  - Implement schedule verification job to ensure DB/Redis consistency
  - Add bulk operations for schedule management
  - _Requirements: 3.2, 5.1, 5.3_

- [x] 6. Update API endpoints for schedule management




- [x] 6.1 Add player schedule management to player service


  - Update player creation to automatically create schedules
  - Update player interval changes to reschedule tasks
  - Update player deletion to clean up schedules
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 6.2 Create schedule monitoring and management endpoints


  - Add endpoint to list all players with their schedule status
  - Add endpoints to pause/resume individual player schedules
  - Add endpoint to manually trigger schedule verification
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 7. Update worker startup and configuration




- [x] 7.1 Remove old scheduler from worker startup


  - Remove custom scheduler startup/shutdown from worker events
  - Update worker configuration to remove scheduler dependencies
  - Clean up old scheduler imports and references
  - _Requirements: 1.1, 1.4_

- [x] 7.2 Add TaskiqScheduler configuration and startup


  - Create scheduler module with TaskiqScheduler configuration
  - Add Redis connection configuration for schedule source
  - Update Docker and deployment configuration for scheduler process
  - _Requirements: 1.1, 1.2, 1.5_

- [x] 8. Implement comprehensive testing





- [x] 8.1 Create unit tests for PlayerScheduleManager


  - Test schedule creation, deletion, and updates
  - Test deterministic schedule ID generation
  - Test error handling and recovery scenarios
  - _Requirements: 2.1, 2.2, 2.3, 3.3_

- [x] 8.2 Create integration tests for scheduler functionality


  - Test end-to-end schedule creation and execution
  - Test TaskiqScheduler integration with Redis
  - Test migration from old to new scheduler
  - _Requirements: 1.1, 1.2, 4.5_
- [x] 9. Update deployment and documentation



- [ ] 9. Update deployment and documentation

- [x] 9.1 Update deployment configuration


  - Add TaskiqScheduler process to Docker Compose
  - Update environment variables for scheduler configuration
  - Create deployment scripts for scheduler migration
  - _Requirements: 1.5_



- [ ] 9.2 Clean up old scheduler code and configuration
  - Remove src/workers/scheduler.py and related files
  - Remove old task configuration files
  - Update documentation to reflect new scheduler approach
  - _Requirements: 1.4_