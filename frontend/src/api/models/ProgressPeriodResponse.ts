/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Response model for progress period information.
 */
export type ProgressPeriodResponse = {
    /**
     * Start date of the analysis period (ISO format)
     */
    start_date: string;
    /**
     * End date of the analysis period (ISO format)
     */
    end_date: string;
    /**
     * Number of days in the analysis period
     */
    days_elapsed: number;
};

