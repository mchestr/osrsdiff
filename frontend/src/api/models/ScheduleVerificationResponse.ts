/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Response model for schedule verification results.
 */
export type ScheduleVerificationResponse = {
    total_schedules: number;
    player_fetch_schedules: number;
    other_schedules: number;
    invalid_schedules: Array<Record<string, any>>;
    orphaned_schedules: Array<string>;
    duplicate_schedules: Record<string, any>;
    verification_timestamp: string;
};

