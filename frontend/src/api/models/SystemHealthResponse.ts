/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */

/**
 * Response model for system health check.
 */
export type SystemHealthResponse = {
    /**
     * Overall system status
     */
    status: string;
    /**
     * Database connection status
     */
    database_connected: boolean;
    /**
     * Total database size in MB
     */
    total_storage_mb: (number | null);
    /**
     * System uptime information
     */
    uptime_info: Record<string, any>;
};

