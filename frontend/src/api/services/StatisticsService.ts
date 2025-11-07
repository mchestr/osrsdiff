/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 
import type { PlayerStatsResponse } from '../models/PlayerStatsResponse';

import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class StatisticsService {

    /**
     * Get Player Stats
     * Get current statistics for a specific player.
     *
     * This endpoint returns the most recent hiscore record for the specified player,
     * including skill levels, experience points, boss kill counts, and calculated
     * combat level.
     *
     * Args:
     * username: OSRS player username
     * statistics_service: Statistics service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * PlayerStatsResponse: Current player statistics
     *
     * Raises:
     * 404 Not Found: Player not found in system
     * 500 Internal Server Error: Service errors
     * @param username
     * @returns PlayerStatsResponse Successful Response
     * @throws ApiError
     */
    public static getPlayerStatsApiV1PlayersUsernameStatsGet(
        username: string,
    ): CancelablePromise<PlayerStatsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/players/{username}/stats',
            path: {
                'username': username,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

}
