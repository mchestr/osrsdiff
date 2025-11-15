/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */


/**
 * Response model for summary generation.
 */
export type GenerateSummaryResponse = {
    /**
     * Success message
     */
    message: string;
    /**
     * Number of summary generation tasks triggered
     */
    tasks_triggered: number;
    /**
     * List of task IDs for triggered tasks
     */
    task_ids: string[];
};

