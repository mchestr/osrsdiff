/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Response model for progress record information.
 */
export type ProgressRecordsResponse = {
    /**
     * ID of the starting hiscore record
     */
    start_record_id?: (number | null);
    /**
     * ID of the ending hiscore record
     */
    end_record_id?: (number | null);
    /**
     * When the start record was fetched (ISO format)
     */
    start_fetched_at?: (string | null);
    /**
     * When the end record was fetched (ISO format)
     */
    end_fetched_at?: (string | null);
};

