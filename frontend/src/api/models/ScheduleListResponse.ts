/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

import type { PlayerScheduleStatusResponse } from './PlayerScheduleStatusResponse';

/**
 * Response model for listing all player schedules.
 */
export type ScheduleListResponse = {
    players: Array<PlayerScheduleStatusResponse>;
    total_count: number;
    scheduled_count: number;
    missing_count: number;
    invalid_count: number;
};

