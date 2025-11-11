/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */

export type TaskExecutionResponse = {
    id: number;
    task_name: string;
    task_args?: Record<string, any> | null;
    status: string;
    retry_count: number;
    schedule_id?: string | null;
    schedule_type?: string | null;
    player_id?: number | null;
    started_at: string;
    completed_at?: string | null;
    duration_seconds?: number | null;
    error_type?: string | null;
    error_message?: string | null;
    error_traceback?: string | null;
    result_data?: Record<string, any> | null;
    execution_metadata?: Record<string, any> | null;
    created_at: string;
};

