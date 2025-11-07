/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Information about a scheduled task.
 */
export type ScheduledTaskInfo = {
    /**
     * Task name
     */
    name: string;
    /**
     * Cron schedule expression
     */
    cron_expression: string;
    /**
     * Task description
     */
    description: string;
    /**
     * Last run timestamp
     */
    last_run: (string | null);
    /**
     * Next scheduled run timestamp
     */
    next_run: string;
    /**
     * Whether task should run now
     */
    should_run_now: boolean;
};

