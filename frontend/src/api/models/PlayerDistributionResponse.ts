/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Response model for player distribution statistics.
 */
export type PlayerDistributionResponse = {
    /**
     * Players grouped by fetch interval
     */
    by_fetch_interval: Record<string, number>;
    /**
     * Players grouped by last fetch time
     */
    by_last_fetch: Record<string, number>;
    /**
     * Players that have never been fetched
     */
    never_fetched: number;
};

