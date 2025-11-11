import { format } from 'date-fns';
import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/apiClient';
import type { TaskExecutionResponse } from '../api/models/TaskExecutionResponse';
import { Modal } from '../components/Modal';

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

const STATUS_OPTIONS = ['success', 'failure', 'retry', 'pending', 'cancelled', 'skipped', 'warning'];

export const TaskExecutions: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize filters from URL params
  const [executions, setExecutions] = useState<TaskExecutionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);

  // Filters - read from URL params on mount
  const [taskNameFilter, setTaskNameFilter] = useState<string>(searchParams.get('task_name') || '');
  const [statusFilter, setStatusFilter] = useState<string>(searchParams.get('status') || '');
  const [scheduleIdFilter, setScheduleIdFilter] = useState<string>(searchParams.get('schedule_id') || '');
  const [playerIdFilter, setPlayerIdFilter] = useState<string>(searchParams.get('player_id') || '');

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalMessage, setModalMessage] = useState<string | React.ReactNode>('');
  const [modalType, setModalType] = useState<'info' | 'error' | 'success' | 'warning'>('info');

  // Update URL params when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (taskNameFilter) params.set('task_name', taskNameFilter);
    if (statusFilter) params.set('status', statusFilter);
    if (scheduleIdFilter) params.set('schedule_id', scheduleIdFilter);
    if (playerIdFilter) params.set('player_id', playerIdFilter);
    setSearchParams(params, { replace: true });
  }, [taskNameFilter, statusFilter, scheduleIdFilter, playerIdFilter, setSearchParams]);

  const fetchExecutions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.SystemService.getTaskExecutionsApiV1SystemTaskExecutionsGet(
        taskNameFilter || null,
        statusFilter || null,
        scheduleIdFilter || null,
        playerIdFilter ? parseInt(playerIdFilter, 10) : null,
        limit,
        offset
      );
      setExecutions(response.executions);
      setTotal(response.total);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch task executions';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  }, [limit, offset, taskNameFilter, statusFilter, scheduleIdFilter, playerIdFilter]);

  useEffect(() => {
    fetchExecutions();
  }, [fetchExecutions]);

  const showModal = (
    title: string,
    message: string | React.ReactNode,
    type: 'info' | 'error' | 'success' | 'warning' = 'info'
  ) => {
    setModalTitle(title);
    setModalMessage(message);
    setModalType(type);
    setModalOpen(true);
  };

  const handleModalClose = () => {
    setModalOpen(false);
  };

  const handleViewDetails = (execution: TaskExecutionResponse) => {
    const details = (
      <div className="space-y-4 text-left">
        <div>
          <h4 className="font-semibold mb-2">Task Information</h4>
          <div className="space-y-1 text-sm">
            <p><span className="font-medium">Task Name:</span> {execution.task_name}</p>
            <p><span className="font-medium">Status:</span> <span style={{ color: STATUS_COLORS[execution.status] || '#fff' }}>{execution.status}</span></p>
            <p><span className="font-medium">Retry Count:</span> {execution.retry_count}</p>
            {execution.schedule_id && <p><span className="font-medium">Schedule ID:</span> {execution.schedule_id}</p>}
            {execution.schedule_type && <p><span className="font-medium">Schedule Type:</span> {execution.schedule_type}</p>}
            {execution.player_id && <p><span className="font-medium">Player ID:</span> {execution.player_id}</p>}
          </div>
        </div>
        {execution.task_args && (
          <div>
            <h4 className="font-semibold mb-2">Task Arguments</h4>
            <pre className="text-xs bg-black p-2 rounded overflow-auto max-h-40">
              {JSON.stringify(execution.task_args, null, 2)}
            </pre>
          </div>
        )}
        <div>
          <h4 className="font-semibold mb-2">Timing</h4>
          <div className="space-y-1 text-sm">
            <p><span className="font-medium">Started:</span> {format(new Date(execution.started_at), 'MMM d, yyyy HH:mm:ss')}</p>
            {execution.completed_at && (
              <p><span className="font-medium">Completed:</span> {format(new Date(execution.completed_at), 'MMM d, yyyy HH:mm:ss')}</p>
            )}
            {execution.duration_seconds !== null && execution.duration_seconds !== undefined && (
              <p><span className="font-medium">Duration:</span> {execution.duration_seconds.toFixed(3)}s</p>
            )}
            <p><span className="font-medium">Created:</span> {format(new Date(execution.created_at), 'MMM d, yyyy HH:mm:ss')}</p>
          </div>
        </div>
        {execution.error_type && (
          <div>
            <h4 className="font-semibold mb-2" style={{ color: '#d32f2f' }}>Error Information</h4>
            <div className="space-y-1 text-sm">
              <p><span className="font-medium">Error Type:</span> {execution.error_type}</p>
              {execution.error_message && (
                <p><span className="font-medium">Error Message:</span> {execution.error_message}</p>
              )}
              {execution.error_traceback && (
                <div>
                  <p className="font-medium mb-1">Traceback:</p>
                  <pre className="text-xs bg-black p-2 rounded overflow-auto max-h-60">
                    {execution.error_traceback}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
        {execution.result_data && (
          <div>
            <h4 className="font-semibold mb-2">Result Data</h4>
            <pre className="text-xs bg-black p-2 rounded overflow-auto max-h-60">
              {JSON.stringify(execution.result_data, null, 2)}
            </pre>
          </div>
        )}
        {execution.execution_metadata && (
          <div>
            <h4 className="font-semibold mb-2">Execution Metadata</h4>
            <pre className="text-xs bg-black p-2 rounded overflow-auto max-h-40">
              {JSON.stringify(execution.execution_metadata, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
    showModal('Task Execution Details', details, 'info');
  };

  const handleResetFilters = () => {
    setTaskNameFilter('');
    setStatusFilter('');
    setScheduleIdFilter('');
    setPlayerIdFilter('');
    setOffset(0);
  };

  const handlePageChange = (newOffset: number) => {
    setOffset(newOffset);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  if (loading && executions.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="osrs-text text-xl">Loading task executions...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="osrs-card-title text-3xl">Task Executions</h1>

      {/* Filters */}
      <div className="osrs-card">
        <h2 className="osrs-card-title mb-4">Filters</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium osrs-text-secondary mb-1">
              Task Name
            </label>
            <input
              type="text"
              value={taskNameFilter}
              onChange={(e) => {
                setTaskNameFilter(e.target.value);
                setOffset(0);
              }}
              placeholder="e.g., fetch_player_hiscores_task"
              className="osrs-btn w-full"
              style={{ backgroundColor: '#3a3024', color: '#ffd700' }}
            />
          </div>
          <div>
            <label className="block text-sm font-medium osrs-text-secondary mb-1">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setOffset(0);
              }}
              className="osrs-btn w-full"
            >
              <option value="">All Statuses</option>
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium osrs-text-secondary mb-1">
              Schedule ID
            </label>
            <input
              type="text"
              value={scheduleIdFilter}
              onChange={(e) => {
                setScheduleIdFilter(e.target.value);
                setOffset(0);
              }}
              placeholder="Schedule ID"
              className="osrs-btn w-full"
              style={{ backgroundColor: '#3a3024', color: '#ffd700' }}
            />
          </div>
          <div>
            <label className="block text-sm font-medium osrs-text-secondary mb-1">
              Player ID
            </label>
            <input
              type="number"
              value={playerIdFilter}
              onChange={(e) => {
                setPlayerIdFilter(e.target.value);
                setOffset(0);
              }}
              placeholder="Player ID"
              className="osrs-btn w-full"
              style={{ backgroundColor: '#3a3024', color: '#ffd700' }}
            />
          </div>
        </div>
        <div className="mt-4 flex flex-col sm:flex-row gap-4">
          <button
            onClick={handleResetFilters}
            className="osrs-btn"
          >
            Reset Filters
          </button>
          <div className="flex items-center gap-2">
            <label className="text-sm osrs-text-secondary">Limit:</label>
            <select
              value={limit}
              onChange={(e) => {
                setLimit(parseInt(e.target.value, 10));
                setOffset(0);
              }}
              className="osrs-btn"
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results Summary */}
      <div className="osrs-card">
        <div className="flex justify-between items-center">
          <p className="osrs-text">
            Showing {executions.length} of {total} executions
          </p>
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => handlePageChange(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="osrs-btn"
                style={{ opacity: offset === 0 ? 0.5 : 1 }}
              >
                Previous
              </button>
              <span className="osrs-text-secondary">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => handlePageChange(offset + limit)}
                disabled={offset + limit >= total}
                className="osrs-btn"
                style={{ opacity: offset + limit >= total ? 0.5 : 1 }}
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Executions Table */}
      <div className="osrs-card">
        <div className="overflow-x-auto">
          <table className="min-w-full" style={{ borderCollapse: 'separate', borderSpacing: 0 }}>
            <thead>
              <tr style={{ backgroundColor: '#1a1510' }}>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  Task Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  Started At
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  Retries
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {executions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center osrs-text-secondary">
                    No task executions found
                  </td>
                </tr>
              ) : (
                executions.map((execution) => (
                  <tr
                    key={execution.id}
                    style={{ borderBottom: '1px solid #8b7355' }}
                    className="hover:opacity-80"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm osrs-text">
                      {execution.id}
                    </td>
                    <td className="px-6 py-4 text-sm osrs-text">
                      <div className="max-w-xs truncate" title={execution.task_name}>
                        {execution.task_name}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className="px-2 inline-flex text-xs leading-5 font-semibold"
                        style={{
                          backgroundColor: `${STATUS_COLORS[execution.status] || '#fff'}20`,
                          border: `1px solid ${STATUS_COLORS[execution.status] || '#fff'}`,
                          color: STATUS_COLORS[execution.status] || '#fff'
                        }}
                      >
                        {execution.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm osrs-text-secondary">
                      {format(new Date(execution.started_at), 'MMM d, yyyy HH:mm:ss')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm osrs-text-secondary">
                      {execution.duration_seconds !== null && execution.duration_seconds !== undefined
                        ? `${execution.duration_seconds.toFixed(3)}s`
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm osrs-text-secondary">
                      {execution.retry_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => handleViewDetails(execution)}
                        className="osrs-text hover:opacity-80"
                        style={{ color: '#d4af37' }}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={handleModalClose}
        title={modalTitle}
        type={modalType}
        showConfirm={false}
      >
        {modalMessage}
      </Modal>
    </div>
  );
};

