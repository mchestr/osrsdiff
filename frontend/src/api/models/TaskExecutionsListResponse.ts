/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */

import type { TaskExecutionResponse } from './TaskExecutionResponse';

export type TaskExecutionsListResponse = {
    total: number;
    limit: number;
    offset: number;
    executions: Array<TaskExecutionResponse>;
};

