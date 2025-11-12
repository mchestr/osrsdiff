import { format } from 'date-fns';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/apiClient';
import type { TaskExecutionResponse } from '../api/models/TaskExecutionResponse';

const STATUS_COLORS: Record<string, string> = {
  success: '#4caf50',
  failure: '#d32f2f',
  retry: '#ff9800',
  pending: '#2196f3',
  running: '#9c27b0',
  cancelled: '#9e9e9e',
  skipped: '#9e9e9e',
  warning: '#ff9800',
  timeout: '#f44336',
};

export const TaskExecutionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [execution, setExecution] = useState<TaskExecutionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchExecution = async () => {
      if (!id) {
        setError('Invalid execution ID');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        // Fetch executions and find the one with matching ID
        // Note: The API doesn't have a single execution endpoint, so we fetch with a large limit
        // and filter client-side. This works but could be optimized with a dedicated endpoint.
        // We fetch in batches to handle cases where the execution might not be in the first batch.
        let found: TaskExecutionResponse | undefined;
        let offset = 0;
        const batchSize = 200;

        while (!found && offset < 10000) {
          const response = await api.SystemService.getTaskExecutionsApiV1SystemTaskExecutionsGet(
            null,
            null,
            null,
            null,
            batchSize,
            offset
          );

          found = response.executions.find((e) => e.id === parseInt(id, 10));
          if (found) {
            break;
          }

          // If we got fewer results than requested, we've reached the end
          if (response.executions.length < batchSize) {
            break;
          }

          offset += batchSize;
        }

        if (found) {
          setExecution(found);
        } else {
          setError('Task execution not found');
        }
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch task execution';
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    fetchExecution();
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="osrs-text text-xl">Loading task execution details...</div>
      </div>
    );
  }

  if (error || !execution) {
    return (
      <div className="space-y-6">
        <div className="osrs-card">
          <h1 className="osrs-card-title text-3xl mb-4">Task Execution Details</h1>
          <div className="osrs-text text-red-400">
            {error || 'Task execution not found'}
          </div>
          <button
            onClick={() => navigate('/task-executions')}
            className="osrs-btn mt-4"
          >
            Back to Task Executions
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="osrs-card-title text-3xl">Task Execution Details</h1>
        <button
          onClick={() => navigate('/task-executions')}
          className="osrs-btn"
        >
          ← Back to Task Executions
        </button>
      </div>

      {/* Task Information */}
      <div className="osrs-card">
        <h2 className="osrs-card-title mb-4">Task Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm osrs-text-secondary mb-1">Task Name</p>
            <p className="osrs-text font-medium">{execution.task_name}</p>
          </div>
          <div>
            <p className="text-sm osrs-text-secondary mb-1">Status</p>
            <span
              className="px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded"
              style={{
                backgroundColor: `${STATUS_COLORS[execution.status] || '#fff'}20`,
                border: `1px solid ${STATUS_COLORS[execution.status] || '#fff'}`,
                color: STATUS_COLORS[execution.status] || '#fff'
              }}
            >
              {execution.status}
            </span>
          </div>
          <div>
            <p className="text-sm osrs-text-secondary mb-1">Retry Count</p>
            <p className="osrs-text">{execution.retry_count}</p>
          </div>
          <div>
            <p className="text-sm osrs-text-secondary mb-1">Execution ID</p>
            <p className="osrs-text">{execution.id}</p>
          </div>
          {execution.schedule_id && (
            <div>
              <p className="text-sm osrs-text-secondary mb-1">Schedule ID</p>
              <p className="osrs-text font-mono text-sm">{execution.schedule_id}</p>
            </div>
          )}
          {execution.schedule_type && (
            <div>
              <p className="text-sm osrs-text-secondary mb-1">Schedule Type</p>
              <p className="osrs-text">{execution.schedule_type}</p>
            </div>
          )}
          {execution.player_id && (
            <div>
              <p className="text-sm osrs-text-secondary mb-1">Player ID</p>
              <p className="osrs-text">{execution.player_id}</p>
            </div>
          )}
        </div>
      </div>

      {/* Timing Information */}
      <div className="osrs-card">
        <h2 className="osrs-card-title mb-4">Timing</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm osrs-text-secondary mb-1">Started At</p>
            <p className="osrs-text">{format(new Date(execution.started_at), 'MMM d, yyyy HH:mm:ss')}</p>
          </div>
          {execution.completed_at && (
            <div>
              <p className="text-sm osrs-text-secondary mb-1">Completed At</p>
              <p className="osrs-text">{format(new Date(execution.completed_at), 'MMM d, yyyy HH:mm:ss')}</p>
            </div>
          )}
          {execution.duration_seconds !== null && execution.duration_seconds !== undefined && (
            <div>
              <p className="text-sm osrs-text-secondary mb-1">Duration</p>
              <p className="osrs-text">{execution.duration_seconds.toFixed(3)}s</p>
            </div>
          )}
          <div>
            <p className="text-sm osrs-text-secondary mb-1">Created At</p>
            <p className="osrs-text">{format(new Date(execution.created_at), 'MMM d, yyyy HH:mm:ss')}</p>
          </div>
        </div>
      </div>

      {/* Task Arguments */}
      {execution.task_args && (
        <div className="osrs-card">
          <h2 className="osrs-card-title mb-4">Task Arguments</h2>
          <pre className="text-sm bg-black p-4 rounded overflow-auto" style={{ maxHeight: '400px' }}>
            {JSON.stringify(execution.task_args, null, 2)}
          </pre>
        </div>
      )}

      {/* Error Information */}
      {execution.error_type && (
        <div className="osrs-card">
          <h2 className="osrs-card-title mb-4" style={{ color: '#d32f2f' }}>Error Information</h2>
          <div className="space-y-4">
            <div>
              <p className="text-sm osrs-text-secondary mb-1">Error Type</p>
              <p className="osrs-text font-mono text-sm">{execution.error_type}</p>
            </div>
            {execution.error_message && (
              <div>
                <p className="text-sm osrs-text-secondary mb-1">Error Message</p>
                <p className="osrs-text font-mono text-sm bg-red-950 p-3 rounded">{execution.error_message}</p>
              </div>
            )}
            {execution.error_traceback && (
              <div>
                <p className="text-sm osrs-text-secondary mb-2">Traceback</p>
                <pre className="text-xs bg-black p-4 rounded overflow-auto font-mono" style={{ maxHeight: '500px' }}>
                  {execution.error_traceback}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Result Data */}
      {execution.result_data && (
        <div className="osrs-card">
          <h2 className="osrs-card-title mb-4">Result Data</h2>
          <pre className="text-sm bg-black p-4 rounded overflow-auto" style={{ maxHeight: '400px' }}>
            {JSON.stringify(execution.result_data, null, 2)}
          </pre>
        </div>
      )}

      {/* Execution Metadata */}
      {execution.execution_metadata && (
        <div className="osrs-card">
          <h2 className="osrs-card-title mb-4">Execution Metadata</h2>
          <pre className="text-sm bg-black p-4 rounded overflow-auto" style={{ maxHeight: '400px' }}>
            {JSON.stringify(execution.execution_metadata, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

