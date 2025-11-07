/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Response model for progress data.
 */
export type ProgressDataResponse = {
    /**
     * Experience gained per skill
     */
    experience_gained: Record<string, number>;
    /**
     * Levels gained per skill
     */
    levels_gained: Record<string, number>;
    /**
     * Boss kills gained
     */
    boss_kills_gained: Record<string, number>;
};

