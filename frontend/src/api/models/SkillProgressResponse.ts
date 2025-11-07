/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

import type { SkillProgressDataResponse } from './SkillProgressDataResponse';
import type { SkillTimelineEntry } from './SkillTimelineEntry';

/**
 * Response model for skill progress analysis.
 */
export type SkillProgressResponse = {
    /**
     * Player username
     */
    username: string;
    /**
     * Skill name
     */
    skill: string;
    /**
     * Number of days analyzed
     */
    period_days: number;
    /**
     * Number of records used in analysis
     */
    total_records: number;
    /**
     * Progress data
     */
    progress: SkillProgressDataResponse;
    /**
     * Timeline of skill progress
     */
    timeline: Array<SkillTimelineEntry>;
};

