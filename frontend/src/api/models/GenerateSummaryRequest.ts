/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */


/**
 * Request model for generating summaries.
 */
export type GenerateSummaryRequest = {
    /**
     * Specific player ID to generate summary for (optional)
     */
    player_id?: (number | null);
    /**
     * Force regeneration even if recent summary exists
     */
    force_regenerate?: boolean;
};

