/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

import type { BossProgressDataResponse } from './BossProgressDataResponse';
import type { BossTimelineEntry } from './BossTimelineEntry';

/**
 * Response model for boss progress analysis.
 */
export type BossProgressResponse = {
    /**
     * Player username
     */
    username: string;
    /**
     * Boss name
     */
    boss: string;
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
    progress: BossProgressDataResponse;
    /**
     * Timeline of boss progress
     */
    timeline: Array<BossTimelineEntry>;
};

