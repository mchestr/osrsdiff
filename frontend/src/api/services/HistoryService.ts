/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */

import type { BossProgressResponse } from '../models/BossProgressResponse';
import type { ProgressAnalysisResponse } from '../models/ProgressAnalysisResponse';
import type { SkillProgressResponse } from '../models/SkillProgressResponse';

import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class HistoryService {

    /**
     * Get Player History
     * Get historical progress analysis for a player.
     *
     * This endpoint analyzes a player's progress between two dates, calculating
     * experience gained, levels gained, boss kills gained, and daily rates.
     *
     * Args:
     * username: OSRS player username
     * start_date: Start date for analysis (ISO format)
     * end_date: End date for analysis (ISO format)
     * days: Alternative to start_date - number of days to look back
     * history_service: History service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * ProgressAnalysisResponse: Progress analysis data
     *
     * Raises:
     * 400 Bad Request: Invalid date parameters
     * 404 Not Found: Player not found
     * 422 Unprocessable Entity: Insufficient data for analysis
     * 500 Internal Server Error: Service errors
     * @param username
     * @param startDate Start date for analysis (ISO format, e.g., '2024-01-01T00:00:00Z'). If not provided, defaults to 30 days ago.
     * @param endDate End date for analysis (ISO format, e.g., '2024-01-31T23:59:59Z'). If not provided, defaults to current time.
     * @param days Number of days to look back from end_date (alternative to start_date). If provided, overrides start_date.
     * @returns ProgressAnalysisResponse Successful Response
     * @throws ApiError
     */
    public static getPlayerHistoryApiV1PlayersUsernameHistoryGet(
        username: string,
        startDate?: (string | null),
        endDate?: (string | null),
        days?: (number | null),
    ): CancelablePromise<ProgressAnalysisResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/players/{username}/history',
            path: {
                'username': username,
            },
            query: {
                'start_date': startDate,
                'end_date': endDate,
                'days': days,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Skill Progress
     * Get progress analysis for a specific skill.
     *
     * This endpoint analyzes a player's progress in a specific skill over a
     * specified number of days, including experience gained, levels gained,
     * and a timeline of progress.
     *
     * Args:
     * username: OSRS player username
     * skill: Skill name (e.g., 'attack', 'defence', 'magic')
     * days: Number of days to analyze (1-365)
     * history_service: History service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * SkillProgressResponse: Skill progress analysis data
     *
     * Raises:
     * 400 Bad Request: Invalid parameters
     * 404 Not Found: Player not found
     * 422 Unprocessable Entity: Insufficient data for analysis
     * 500 Internal Server Error: Service errors
     * @param username
     * @param skill
     * @param days Number of days to analyze
     * @returns SkillProgressResponse Successful Response
     * @throws ApiError
     */
    public static getSkillProgressApiV1PlayersUsernameHistorySkillsSkillGet(
        username: string,
        skill: string,
        days: number = 30,
    ): CancelablePromise<SkillProgressResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/players/{username}/history/skills/{skill}',
            path: {
                'username': username,
                'skill': skill,
            },
            query: {
                'days': days,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Boss Progress
     * Get progress analysis for a specific boss.
     *
     * This endpoint analyzes a player's progress against a specific boss over a
     * specified number of days, including kills gained and a timeline of progress.
     *
     * Args:
     * username: OSRS player username
     * boss: Boss name (e.g., 'zulrah', 'vorkath', 'chambers_of_xeric')
     * days: Number of days to analyze (1-365)
     * history_service: History service dependency
     * current_user: Authenticated user information
     *
     * Returns:
     * BossProgressResponse: Boss progress analysis data
     *
     * Raises:
     * 400 Bad Request: Invalid parameters
     * 404 Not Found: Player not found
     * 422 Unprocessable Entity: Insufficient data for analysis
     * 500 Internal Server Error: Service errors
     * @param username
     * @param boss
     * @param days Number of days to analyze
     * @returns BossProgressResponse Successful Response
     * @throws ApiError
     */
    public static getBossProgressApiV1PlayersUsernameHistoryBossesBossGet(
        username: string,
        boss: string,
        days: number = 30,
    ): CancelablePromise<BossProgressResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/players/{username}/history/bosses/{boss}',
            path: {
                'username': username,
                'boss': boss,
            },
            query: {
                'days': days,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Player Records
     * Get top exp gains per day for a player across different time periods.
     * @param username
     * @returns PlayerRecordsResponse Successful Response
     * @throws ApiError
     */
    public static getPlayerRecordsApiV1PlayersUsernameRecordsGet(
        username: string,
    ): CancelablePromise<{
        username: string;
        records: {
            day: Record<string, { skill: string; exp_gain: number; date: string; start_exp: number; end_exp: number }>;
            week: Record<string, { skill: string; exp_gain: number; date: string; start_exp: number; end_exp: number }>;
            month: Record<string, { skill: string; exp_gain: number; date: string; start_exp: number; end_exp: number }>;
            year: Record<string, { skill: string; exp_gain: number; date: string; start_exp: number; end_exp: number }>;
        };
    }> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/players/{username}/records',
            path: {
                'username': username,
            },
        });
    }

}
