/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */

import type { CostStatsResponse } from '../models/OpenAICostStatsResponse';
import type { DatabaseStatsResponse } from '../models/DatabaseStatsResponse';
import type { GenerateSummaryRequest } from '../models/GenerateSummaryRequest';
import type { GenerateSummaryResponse } from '../models/GenerateSummaryResponse';
import type { PlayerDistributionResponse } from '../models/PlayerDistributionResponse';
import type { ScheduledTasksResponse } from '../models/ScheduledTasksResponse';
import type { SystemHealthResponse } from '../models/SystemHealthResponse';
import type { TaskExecutionsListResponse } from '../models/TaskExecutionsListResponse';
import type { TaskTriggerResponse } from '../models/TaskTriggerResponse';

import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class SystemService {

    /**
     * Get Database Stats
     * Get comprehensive database statistics.
     *
     * Returns detailed statistics about players, hiscore records, and system usage.
     * Useful for monitoring system growth and usage patterns.
     *
     * Args:
     * db_session: Database session dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * DatabaseStatsResponse: Comprehensive database statistics
     *
     * Raises:
     * 500 Internal Server Error: Database or calculation errors
     * @returns DatabaseStatsResponse Successful Response
     * @throws ApiError
     */
    public static getDatabaseStatsApiV1SystemStatsGet(): CancelablePromise<DatabaseStatsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/system/stats',
        });
    }

    /**
     * Get System Health
     * Get system health information.
     *
     * Returns overall system status, database connectivity, and storage information.
     *
     * Args:
     * db_session: Database session dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * SystemHealthResponse: System health information
     *
     * Raises:
     * 500 Internal Server Error: Health check errors
     * @returns SystemHealthResponse Successful Response
     * @throws ApiError
     */
    public static getSystemHealthApiV1SystemHealthGet(): CancelablePromise<SystemHealthResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/system/health',
        });
    }

    /**
     * Get Player Distribution
     * Get player distribution statistics.
     *
     * Returns information about how players are distributed across different
     * fetch intervals and last fetch times.
     *
     * Args:
     * db_session: Database session dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * PlayerDistributionResponse: Player distribution statistics
     *
     * Raises:
     * 500 Internal Server Error: Database or calculation errors
     * @returns PlayerDistributionResponse Successful Response
     * @throws ApiError
     */
    public static getPlayerDistributionApiV1SystemDistributionGet(): CancelablePromise<PlayerDistributionResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/system/distribution',
        });
    }

    /**
     * Get Scheduled Tasks
     * Get information about all scheduled tasks.
     *
     * Returns details about each scheduled task including their cron expressions,
     * last run times, next run times, and current status.
     *
     * Note: This endpoint now returns information about TaskIQ scheduled tasks
     * managed by the TaskiqScheduler instead of the old custom scheduler.
     *
     * Args:
     * current_user: Authenticated user information
     *
     * Returns:
     * ScheduledTasksResponse: List of scheduled tasks with their information
     *
     * Raises:
     * 500 Internal Server Error: Scheduler errors
     * @returns ScheduledTasksResponse Successful Response
     * @throws ApiError
     */
    public static getScheduledTasksApiV1SystemScheduledTasksGet(): CancelablePromise<ScheduledTasksResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/system/scheduled-tasks',
        });
    }

    /**
     * Trigger Scheduled Task
     * Manually trigger any scheduled task.
     *
     * This endpoint allows administrators to manually trigger any scheduled task
     * without waiting for its scheduled time. Currently supports triggering
     * TaskIQ tasks directly.
     *
     * Args:
     * task_name: Name of the task to trigger (e.g., "check_game_mode_downgrades_task")
     * current_user: Authenticated user information
     *
     * Returns:
     * TaskTriggerResponse: Confirmation that the task was triggered
     *
     * Raises:
     * 404 Not Found: Task not found
     * 500 Internal Server Error: Task trigger errors
     * @param taskName
     * @returns TaskTriggerResponse Successful Response
     * @throws ApiError
     */
    public static triggerScheduledTaskApiV1SystemTriggerTaskTaskNamePost(
        taskName: string,
    ): CancelablePromise<TaskTriggerResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/system/trigger-task/{task_name}',
            path: {
                'task_name': taskName,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Task Executions
     * Get task execution history with search functionality.
     *
     * This endpoint allows querying task execution history to debug why tasks
     * may not have executed at scheduled times. Supports searching across task name,
     * status, schedule_id, and player_name.
     *
     * @param search Search term that matches task name, status, schedule_id, or player_name (partial match)
     * @param limit Maximum number of results to return (default: 50, max: 200)
     * @param offset Number of results to skip for pagination
     * @returns TaskExecutionsListResponse Successful Response
     * @throws ApiError
     */
    public static getTaskExecutionsApiV1SystemTaskExecutionsGet(
        search?: string | null,
        limit?: number,
        offset?: number,
    ): CancelablePromise<TaskExecutionsListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/system/task-executions',
            query: {
                'search': search,
                'limit': limit,
                'offset': offset,
            },
        });
    }

    /**
     * Get Cost Stats
     * Get API cost statistics based on summary generation usage.
     *
     * Calculates estimated costs from token usage stored in player summaries.
     * Supports cost breakdown by model and time periods (24h, 7d, 30d).
     * Works with any AI provider (OpenAI, Anthropic, etc.) based on model name.
     *
     * Args:
     * db_session: Database session dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * CostStatsResponse: Cost statistics
     *
     * Raises:
     * 500 Internal Server Error: Database or calculation errors
     * @returns CostStatsResponse Successful Response
     * @throws ApiError
     */
    public static getCostsApiV1SystemCostsGet(): CancelablePromise<CostStatsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/system/costs',
        });
    }

    /**
     * Generate Summaries
     * Trigger AI-powered progress summary generation for players.
     *
     * This endpoint triggers asynchronous background tasks to generate summaries
     * using OpenAI API that analyze player progress over the last day and week.
     * Admins can trigger this for all players or a specific player. The API returns
     * immediately after enqueuing tasks without waiting for summary generation.
     *
     * Args:
     * request: Summary generation request with optional player_id
     * db_session: Database session dependency
     * current_user: Authenticated admin user information
     *
     * Returns:
     * GenerateSummaryResponse: Number of tasks triggered and their IDs
     *
     * Raises:
     * 403 Forbidden: User is not an admin
     * 404 Not Found: Player not found (if player_id specified)
     * 500 Internal Server Error: Task enqueue errors
     * @param requestBody
     * @returns GenerateSummaryResponse Successful Response
     * @throws ApiError
     */
    public static generateSummariesApiV1SystemGenerateSummariesPost(
        requestBody: GenerateSummaryRequest,
    ): CancelablePromise<GenerateSummaryResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/system/generate-summaries',
            body: requestBody,
            mediaType: 'application/json',
        });
    }

}
