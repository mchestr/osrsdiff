/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */


/**
 * Response model for player data.
 */
export type PlayerResponse = {
    id: number;
    username: string;
    created_at: string;
    last_fetched: (string | null);
    is_active: boolean;
    fetch_interval_minutes: number;
    /**
     * TaskIQ schedule ID for this player's fetch task
     */
    schedule_id: (string | null);
    /**
     * Player game mode (regular, ironman, hardcore, ultimate)
     */
    game_mode?: (string | null);
};

