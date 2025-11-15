/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */

import type { FetchTriggerResponse } from '../models/FetchTriggerResponse';
import type { MessageResponse } from '../models/MessageResponse';
import type { PlayerCreateRequest } from '../models/PlayerCreateRequest';
import type { PlayerMetadataResponse } from '../models/PlayerMetadataResponse';
import type { PlayerResponse } from '../models/PlayerResponse';
import type { PlayersListResponse } from '../models/PlayersListResponse';
import type { PlayerUpdateIntervalRequest } from '../models/PlayerUpdateIntervalRequest';
import type { ScheduleListResponse } from '../models/ScheduleListResponse';
import type { ScheduleVerificationResponse } from '../models/ScheduleVerificationResponse';

import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class PlayersService {

    /**
     * Add Player
     * Add a new player to the tracking system.
     *
     * This endpoint validates the username, checks if the player exists in OSRS hiscores,
     * prevents duplicates, and creates a new Player entity. It also schedules periodic
     * hiscore fetches based on the player's fetch interval and triggers an initial fetch
     * task to populate baseline statistics.
     *
     * Args:
     * request: Player creation request with username
     * player_service: Player service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * PlayerResponse: Created player information with schedule_id
     *
     * Raises:
     * 400 Bad Request: Invalid username format
     * 404 Not Found: Player not found in OSRS hiscores
     * 409 Conflict: Player already exists in system
     * 502 Bad Gateway: OSRS API unavailable
     * 500 Internal Server Error: Other service errors
     * @param requestBody
     * @returns PlayerResponse Successful Response
     * @throws ApiError
     */
    public static addPlayerApiV1PlayersPost(
        requestBody: PlayerCreateRequest,
    ): CancelablePromise<PlayerResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/players',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * List Players
     * List all tracked players in the system.
     *
     * Args:
     * active_only: If True, only return active players. If False, return all players.
     * player_service: Player service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * PlayersListResponse: List of players with total count
     *
     * Raises:
     * 500 Internal Server Error: Service errors
     * @param activeOnly
     * @returns PlayersListResponse Successful Response
     * @throws ApiError
     */
    public static listPlayersApiV1PlayersGet(
        activeOnly: boolean = true,
    ): CancelablePromise<PlayersListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/players',
            query: {
                'active_only': activeOnly,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Remove Player
     * Remove a player from the tracking system.
     *
     * This endpoint removes the player and all associated hiscore records
     * from the database. This action cannot be undone.
     *
     * Args:
     * username: OSRS player username to remove
     * player_service: Player service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * MessageResponse: Confirmation message
     *
     * Raises:
     * 404 Not Found: Player not found in system
     * 500 Internal Server Error: Service errors
     * @param username
     * @returns MessageResponse Successful Response
     * @throws ApiError
     */
    public static removePlayerApiV1PlayersUsernameDelete(
        username: string,
    ): CancelablePromise<MessageResponse> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/players/{username}',
            path: {
                'username': username,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Trigger Manual Fetch
     * Trigger a manual hiscore data fetch for a specific player.
     *
     * This endpoint enqueues a background task to fetch the latest hiscore data
     * from the OSRS API for the specified player. The task will run asynchronously
     * and the response includes a task ID for tracking progress.
     *
     * Args:
     * username: OSRS player username to fetch data for
     * player_service: Player service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * FetchTriggerResponse: Task information with ID and estimated completion time
     *
     * Raises:
     * 404 Not Found: Player not found in tracking system
     * 500 Internal Server Error: Task enqueue or other service errors
     * @param username
     * @returns FetchTriggerResponse Successful Response
     * @throws ApiError
     */
    public static triggerManualFetchApiV1PlayersUsernameFetchPost(
        username: string,
    ): CancelablePromise<FetchTriggerResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/players/{username}/fetch',
            path: {
                'username': username,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Player Metadata
     * Get detailed metadata and statistics for a specific player.
     *
     * Returns comprehensive information about a player including record counts,
     * fetch history, and timing statistics. Useful for monitoring individual
     * player tracking performance and troubleshooting.
     *
     * Args:
     * username: OSRS player username
     * db_session: Database session dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * PlayerMetadataResponse: Detailed player metadata and statistics
     *
     * Raises:
     * 404 Not Found: Player not found in system
     * 500 Internal Server Error: Database or calculation errors
     * @param username
     * @returns PlayerMetadataResponse Successful Response
     * @throws ApiError
     */
    public static getPlayerMetadataApiV1PlayersUsernameMetadataGet(
        username: string,
    ): CancelablePromise<PlayerMetadataResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/players/{username}/metadata',
            path: {
                'username': username,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Player Summary
     * Get the most recent AI-generated summary for a player.
     *
     * Returns the latest summary if available, or None if no summary exists.
     *
     * Args:
     * username: OSRS player username
     * db_session: Database session dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * PlayerSummaryResponse: Most recent summary or None
     *
     * Raises:
     * 404 Not Found: Player not found in system
     * 500 Internal Server Error: Database errors
     * @param username
     * @returns PlayerSummaryResponse Successful Response
     * @throws ApiError
     */
    public static getPlayerSummaryApiV1PlayersUsernameSummaryGet(
        username: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/players/{username}/summary',
            path: {
                'username': username,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Deactivate Player
     * Deactivate a player (soft delete) to stop automatic fetching.
     *
     * This sets is_active to False, which stops automatic hiscore fetching
     * but preserves all historical data. The player can be reactivated later.
     *
     * Args:
     * username: OSRS player username to deactivate
     * player_service: Player service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * MessageResponse: Confirmation message
     *
     * Raises:
     * 404 Not Found: Player not found in system
     * 500 Internal Server Error: Service errors
     * @param username
     * @returns MessageResponse Successful Response
     * @throws ApiError
     */
    public static deactivatePlayerApiV1PlayersUsernameDeactivatePost(
        username: string,
    ): CancelablePromise<MessageResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/players/{username}/deactivate',
            path: {
                'username': username,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Reactivate Player
     * Reactivate a previously deactivated player.
     *
     * This sets is_active to True, which resumes automatic hiscore fetching
     * according to the player's fetch interval.
     *
     * Args:
     * username: OSRS player username to reactivate
     * player_service: Player service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * MessageResponse: Confirmation message
     *
     * Raises:
     * 404 Not Found: Player not found in system
     * 500 Internal Server Error: Service errors
     * @param username
     * @returns MessageResponse Successful Response
     * @throws ApiError
     */
    public static reactivatePlayerApiV1PlayersUsernameReactivatePost(
        username: string,
    ): CancelablePromise<MessageResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/players/{username}/reactivate',
            path: {
                'username': username,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Update Player Fetch Interval
     * Update a player's fetch interval and reschedule their task.
     *
     * This endpoint updates the player's fetch interval and automatically
     * reschedules their background task with the new interval if they are active.
     *
     * Args:
     * username: OSRS player username to update
     * request: Update request with new fetch interval
     * player_service: Player service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * PlayerResponse: Updated player information
     *
     * Raises:
     * 400 Bad Request: Invalid fetch interval
     * 404 Not Found: Player not found in system
     * 500 Internal Server Error: Service errors
     * @param username
     * @param requestBody
     * @returns PlayerResponse Successful Response
     * @throws ApiError
     */
    public static updatePlayerFetchIntervalApiV1PlayersUsernameFetchIntervalPut(
        username: string,
        requestBody: PlayerUpdateIntervalRequest,
    ): CancelablePromise<PlayerResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/players/{username}/fetch-interval',
            path: {
                'username': username,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * List Player Schedules
     * List all players with their schedule status.
     *
     * This endpoint provides comprehensive information about all players and
     * their scheduling status, including whether schedules exist, are valid,
     * or are missing.
     *
     * Args:
     * player_service: Player service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * ScheduleListResponse: List of players with schedule status information
     *
     * Raises:
     * 500 Internal Server Error: Service errors
     * @returns ScheduleListResponse Successful Response
     * @throws ApiError
     */
    public static listPlayerSchedulesApiV1PlayersSchedulesGet(): CancelablePromise<ScheduleListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/players/schedules',
        });
    }

    /**
     * Verify All Schedules
     * Manually trigger schedule verification for all players.
     *
     * This endpoint runs a comprehensive verification of all schedules in Redis
     * and returns a detailed report of any issues found.
     *
     * Args:
     * current_user: Authenticated user information
     *
     * Returns:
     * ScheduleVerificationResponse: Detailed verification report
     *
     * Raises:
     * 500 Internal Server Error: Service errors
     * @returns ScheduleVerificationResponse Successful Response
     * @throws ApiError
     */
    public static verifyAllSchedulesApiV1PlayersSchedulesVerifyPost(): CancelablePromise<ScheduleVerificationResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/players/schedules/verify',
        });
    }

}
