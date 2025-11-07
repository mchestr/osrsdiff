/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Response model for task trigger operations.
 */
export type TaskTriggerResponse = {
    /**
     * Name of the triggered task
     */
    task_name: string;
    /**
     * Success message
     */
    message: string;
    /**
     * When the task was triggered
     */
    timestamp: string;
};

