/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

import type { ScheduledTaskInfo } from './ScheduledTaskInfo';

/**
 * Response model for scheduled tasks list.
 */
export type ScheduledTasksResponse = {
    /**
     * List of scheduled tasks
     */
    tasks: Array<ScheduledTaskInfo>;
    /**
     * Total number of tasks
     */
    total_count: number;
};

