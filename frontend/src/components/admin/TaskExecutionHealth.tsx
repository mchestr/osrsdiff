import { Link } from 'react-router-dom';
import type { TaskExecutionResponse } from '../../api/models/TaskExecutionResponse';
import { TaskExecutionChart } from './TaskExecutionChart';
import { StatusBreakdown } from './StatusBreakdown';
import type { ExecutionSummary } from './types';

interface TaskExecutionHealthProps {
  executionSummary: ExecutionSummary | null;
  executionsForGraph: TaskExecutionResponse[];
  loading: boolean;
}

export const TaskExecutionHealth: React.FC<TaskExecutionHealthProps> = ({
  executionSummary,
  executionsForGraph,
  loading,
}) => {
  if (loading) {
    return (
      <div className="osrs-card">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 sm:gap-4 mb-3 sm:mb-4">
          <h2 className="osrs-card-title mb-0 text-lg sm:text-xl">Task Execution Health</h2>
          <Link
            to="/task-executions"
            className="osrs-btn text-sm"
            style={{ minWidth: 'auto', padding: '0.5rem 1rem' }}
          >
            View All →
          </Link>
        </div>
        <div className="flex items-center justify-center py-4">
          <div className="osrs-text-secondary">Loading summary...</div>
        </div>
      </div>
    );
  }

  if (!executionSummary) {
    return (
      <div className="osrs-card">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 sm:gap-4 mb-3 sm:mb-4">
          <h2 className="osrs-card-title mb-0 text-lg sm:text-xl">Task Execution Health</h2>
          <Link
            to="/task-executions"
            className="osrs-btn text-sm"
            style={{ minWidth: 'auto', padding: '0.5rem 1rem' }}
          >
            View All →
          </Link>
        </div>
        <div className="flex items-center justify-center py-4">
          <div className="osrs-text-secondary">No execution data available</div>
        </div>
      </div>
    );
  }

  const getStatusColor = (value: number, thresholds: { good: number; warning: number }, reverse = false) => {
    if (reverse) {
      return value <= thresholds.good ? '#4caf50' : value <= thresholds.warning ? '#ff9800' : '#d32f2f';
    }
    return value >= thresholds.good ? '#4caf50' : value >= thresholds.warning ? '#ff9800' : '#d32f2f';
  };

  return (
    <div className="osrs-card">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 sm:gap-4 mb-3 sm:mb-4">
        <h2 className="osrs-card-title mb-0 text-lg sm:text-xl">Task Execution Health</h2>
        <Link
          to="/task-executions"
          className="osrs-btn text-sm"
          style={{ minWidth: 'auto', padding: '0.5rem 1rem' }}
        >
          View All →
        </Link>
      </div>
      <div className="space-y-4">
        {/* Task Executions Over Time Graph */}
        {executionsForGraph.length > 0 && (
          <TaskExecutionChart executions={executionsForGraph} />
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div className="flex flex-col">
            <h3 className="osrs-stat-label mb-1" style={{ minHeight: '2.5rem' }}>Total Executions</h3>
            <Link
              to="/task-executions"
              className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
              style={{ textDecoration: 'none' }}
            >
              {executionSummary.total.toLocaleString()}
            </Link>
          </div>
          <div className="flex flex-col">
            <h3 className="osrs-stat-label mb-1" style={{ minHeight: '2.5rem' }}>Success Rate</h3>
            <Link
              to="/task-executions?status=success"
              className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
              style={{
                color: getStatusColor(executionSummary.successRate, { good: 95, warning: 80 }),
                textDecoration: 'none'
              }}
            >
              {executionSummary.successRate.toFixed(1)}%
            </Link>
          </div>
          <div className="flex flex-col">
            <h3 className="osrs-stat-label mb-1" style={{ minHeight: '2.5rem' }}>Failure Rate</h3>
            <Link
              to="/task-executions?status=failure"
              className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
              style={{
                color: getStatusColor(executionSummary.failureRate, { good: 5, warning: 20 }, true),
                textDecoration: 'none'
              }}
            >
              {executionSummary.failureRate.toFixed(1)}%
            </Link>
          </div>
          <div className="flex flex-col">
            <h3 className="osrs-stat-label mb-1" style={{ minHeight: '2.5rem' }}>Avg Duration</h3>
            <p className="osrs-stat-value block">
              {executionSummary.avgDuration > 0
                ? `${executionSummary.avgDuration.toFixed(2)}s`
                : '-'}
            </p>
          </div>
          <div className="flex flex-col">
            <h3 className="osrs-stat-label mb-1" style={{ minHeight: '2.5rem' }}>Failures (24h)</h3>
            <Link
              to="/task-executions?status=failure"
              className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
              style={{
                color: getStatusColor(executionSummary.recentFailures24h, { good: 0, warning: 5 }, true),
                textDecoration: 'none'
              }}
            >
              {executionSummary.recentFailures24h}
            </Link>
          </div>
          <div className="flex flex-col">
            <h3 className="osrs-stat-label mb-1" style={{ minHeight: '2.5rem' }}>Failures (7d)</h3>
            <Link
              to="/task-executions?status=failure"
              className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
              style={{
                color: getStatusColor(executionSummary.recentFailures7d, { good: 0, warning: 20 }, true),
                textDecoration: 'none'
              }}
            >
              {executionSummary.recentFailures7d}
            </Link>
          </div>
        </div>

        {/* Status Breakdown */}
        <StatusBreakdown executionSummary={executionSummary} />

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t border-secondary-200 dark:border-secondary-700">
          <div className="flex flex-col">
            <h3 className="osrs-stat-label mb-1" style={{ minHeight: '2.5rem' }}>Successes</h3>
            <Link
              to="/task-executions?status=success"
              className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
              style={{ color: '#4caf50', textDecoration: 'none' }}
            >
              {executionSummary.successCount.toLocaleString()}
            </Link>
          </div>
          <div className="flex flex-col">
            <h3 className="osrs-stat-label mb-1" style={{ minHeight: '2.5rem' }}>Failures</h3>
            <Link
              to="/task-executions?status=failure"
              className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
              style={{ color: '#d32f2f', textDecoration: 'none' }}
            >
              {executionSummary.failureCount.toLocaleString()}
            </Link>
          </div>
          <div className="flex flex-col">
            <h3 className="osrs-stat-label mb-1" style={{ minHeight: '2.5rem' }}>Retries</h3>
            <Link
              to="/task-executions?status=retry"
              className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
              style={{ color: '#ff9800', textDecoration: 'none' }}
            >
              {executionSummary.retryCount.toLocaleString()}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

