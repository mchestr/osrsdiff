/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Response model for player metadata and admin information.
 */
export type PlayerMetadataResponse = {
    id: number;
    username: string;
    created_at: string;
    last_fetched: (string | null);
    is_active: boolean;
    fetch_interval_minutes: number;
    /**
     * TaskIQ schedule ID for this player's fetch task
     */
    schedule_id: (string | null);
    /**
     * Total number of hiscore records
     */
    total_records: number;
    /**
     * Timestamp of first hiscore record
     */
    first_record: (string | null);
    /**
     * Timestamp of latest hiscore record
     */
    latest_record: (string | null);
    /**
     * Records created in last 24 hours
     */
    records_last_24h: number;
    /**
     * Records created in last 7 days
     */
    records_last_7d: number;
    /**
     * Average time between fetches in hours
     */
    avg_fetch_frequency_hours: (number | null);
};

