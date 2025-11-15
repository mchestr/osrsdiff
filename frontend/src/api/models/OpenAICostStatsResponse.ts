/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */


/**
 * Response model for cost statistics.
 */
export type CostStatsResponse = {
    /**
     * Total number of summaries generated
     */
    total_summaries: number;
    /**
     * Total prompt tokens used
     */
    total_prompt_tokens: number;
    /**
     * Total completion tokens used
     */
    total_completion_tokens: number;
    /**
     * Total tokens used (prompt + completion)
     */
    total_tokens: number;
    /**
     * Total estimated cost in USD
     */
    total_cost_usd: number;
    /**
     * Estimated cost in last 24 hours
     */
    cost_last_24h_usd: number;
    /**
     * Estimated cost in last 7 days
     */
    cost_last_7d_usd: number;
    /**
     * Estimated cost in last 30 days
     */
    cost_last_30d_usd: number;
    /**
     * Cost breakdown by model
     */
    by_model: Record<string, {
        count: number;
        prompt_tokens: number;
        completion_tokens: number;
        total_tokens: number;
        cost_usd: number;
    }>;
};

