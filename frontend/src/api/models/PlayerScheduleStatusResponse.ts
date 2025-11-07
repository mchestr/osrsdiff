/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Response model for player schedule status.
 */
export type PlayerScheduleStatusResponse = {
    id: number;
    username: string;
    is_active: boolean;
    fetch_interval_minutes: number;
    schedule_id: (string | null);
    /**
     * Status of the schedule: 'scheduled', 'missing', 'invalid', 'not_scheduled'
     */
    schedule_status: string;
    /**
     * Timestamp when schedule was last verified
     */
    last_verified: (string | null);
};

