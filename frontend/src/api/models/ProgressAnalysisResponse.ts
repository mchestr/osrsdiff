/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 

import type { ProgressDataResponse } from './ProgressDataResponse';
import type { ProgressPeriodResponse } from './ProgressPeriodResponse';
import type { ProgressRatesResponse } from './ProgressRatesResponse';
import type { ProgressRecordsResponse } from './ProgressRecordsResponse';

/**
 * Response model for progress analysis.
 */
export type ProgressAnalysisResponse = {
    /**
     * Player username
     */
    username: string;
    /**
     * Analysis period information
     */
    period: ProgressPeriodResponse;
    /**
     * Record information
     */
    records: ProgressRecordsResponse;
    /**
     * Progress data
     */
    progress: ProgressDataResponse;
    /**
     * Progress rates
     */
    rates: ProgressRatesResponse;
};

