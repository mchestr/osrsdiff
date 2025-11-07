/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Response model for progress rates.
 */
export type ProgressRatesResponse = {
    /**
     * Daily experience rates per skill
     */
    daily_experience: Record<string, number>;
    /**
     * Daily boss kill rates
     */
    daily_boss_kills: Record<string, number>;
};

