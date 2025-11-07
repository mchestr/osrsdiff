/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

/**
 * Response model for skill timeline entry.
 */
export type SkillTimelineEntry = {
    /**
     * Date of the record (ISO format)
     */
    date: string;
    /**
     * Skill level at this date
     */
    level?: (number | null);
    /**
     * Skill experience at this date
     */
    experience?: (number | null);
};

