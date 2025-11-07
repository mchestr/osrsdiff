/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Response model for manual fetch trigger.
 */
export type FetchTriggerResponse = {
    task_id: string;
    username: string;
    message: string;
    estimated_completion_seconds: number;
    status?: string;
};

