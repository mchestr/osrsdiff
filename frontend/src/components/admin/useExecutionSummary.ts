import { useMemo } from 'react';
import type { TaskExecutionResponse } from '../../api/models/TaskExecutionResponse';
import type { ExecutionSummary } from './types';

export const useExecutionSummary = (
  executions: TaskExecutionResponse[],
  total: number
): ExecutionSummary | null => {
  return useMemo(() => {
    if (executions.length === 0) return null;

    const now = new Date();
    const last24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const last7d = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    // Calculate statistics
    const successCount = executions.filter(e => e.status === 'success').length;
    const failureCount = executions.filter(e => e.status === 'failure').length;
    const retryCount = executions.filter(e => e.status === 'retry').length;
    const pendingCount = executions.filter(e => e.status === 'pending').length;

    const successRate = total > 0 ? (successCount / total) * 100 : 0;
    const failureRate = total > 0 ? (failureCount / total) * 100 : 0;

    // Calculate average duration from completed executions
    const completedExecutions = executions.filter(
      e => e.duration_seconds !== null && e.duration_seconds !== undefined
    );
    const avgDuration = completedExecutions.length > 0
      ? completedExecutions.reduce((sum, e) => sum + (e.duration_seconds || 0), 0) / completedExecutions.length
      : 0;

    // Count recent failures
    const recentFailures24h = executions.filter(
      e => e.status === 'failure' && new Date(e.started_at) >= last24h
    ).length;
    const recentFailures7d = executions.filter(
      e => e.status === 'failure' && new Date(e.started_at) >= last7d
    ).length;

    // Status breakdown
    const statusBreakdown: Record<string, number> = {};
    executions.forEach(e => {
      statusBreakdown[e.status] = (statusBreakdown[e.status] || 0) + 1;
    });

    return {
      total,
      successCount,
      failureCount,
      retryCount,
      pendingCount,
      successRate,
      failureRate,
      avgDuration,
      recentFailures24h,
      recentFailures7d,
      statusBreakdown,
    };
  }, [executions, total]);
};

