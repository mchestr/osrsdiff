/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

import type { OverallStatsResponse } from './OverallStatsResponse';
import type { StatsMetadataResponse } from './StatsMetadataResponse';

/**
 * Response model for individual player statistics.
 */
export type PlayerStatsResponse = {
    /**
     * Player username
     */
    username: string;
    /**
     * When the data was last fetched (ISO format)
     */
    fetched_at?: (string | null);
    /**
     * Overall statistics
     */
    overall?: (OverallStatsResponse | null);
    /**
     * Calculated combat level
     */
    combat_level?: (number | null);
    /**
     * Skills data with levels and experience
     */
    skills?: Record<string, any>;
    /**
     * Boss kill counts and ranks
     */
    bosses?: Record<string, any>;
    /**
     * Additional metadata about the record
     */
    metadata: StatsMetadataResponse;
    /**
     * Error message if data unavailable
     */
    error?: (string | null);
};

