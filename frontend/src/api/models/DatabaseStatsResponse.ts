/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Response model for database statistics.
 */
export type DatabaseStatsResponse = {
    /**
     * Total number of players in system
     */
    total_players: number;
    /**
     * Number of active players
     */
    active_players: number;
    /**
     * Number of inactive players
     */
    inactive_players: number;
    /**
     * Total number of hiscore records
     */
    total_hiscore_records: number;
    /**
     * Timestamp of oldest hiscore record
     */
    oldest_record: (string | null);
    /**
     * Timestamp of newest hiscore record
     */
    newest_record: (string | null);
    /**
     * Records created in last 24 hours
     */
    records_last_24h: number;
    /**
     * Records created in last 7 days
     */
    records_last_7d: number;
    /**
     * Average records per player
     */
    avg_records_per_player: number;
};

