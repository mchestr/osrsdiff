import { format } from 'date-fns';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api/apiClient';
import type { TaskExecutionResponse } from '../api/models/TaskExecutionResponse';
import { Modal } from '../components/Modal';

// Constants
const DEBOUNCE_DELAY_MS = 500;
const DEFAULT_LIMIT = 50;
const LIMIT_OPTIONS = [25, 50, 100, 200] as const;

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
} as const;

// Types
type ModalType = 'info' | 'error' | 'success' | 'warning';

interface ModalState {
  isOpen: boolean;
  title: string;
  message: string | React.ReactNode;
  type: ModalType;
}

// Custom hooks
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

function useUrlSync(
  searchParams: URLSearchParams,
  setSearchParams: (params: URLSearchParams, options?: { replace?: boolean }) => void,
  activeSearch: string | null,
  limit: number
): void {
  // Sync state to URL when search or limit changes
  useEffect(() => {
    const currentSearch = searchParams.get('search') || '';
    const currentLimit = searchParams.get('limit');
    const newSearch = activeSearch || '';
    const newLimit = limit !== DEFAULT_LIMIT ? limit.toString() : '';

    // Only update if params actually changed
    if (currentSearch !== newSearch || currentLimit !== newLimit) {
      const params = new URLSearchParams();

      if (activeSearch) {
        params.set('search', activeSearch);
      }
      if (limit !== DEFAULT_LIMIT) {
        params.set('limit', limit.toString());
      }

      setSearchParams(params, { replace: true });
    }
  }, [activeSearch, limit, searchParams, setSearchParams]);
}

// Component
export const TaskExecutions: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Search state
  const [searchInput, setSearchInput] = useState<string>(() =>
    searchParams.get('search') || ''
  );
  const debouncedSearch = useDebounce(searchInput, DEBOUNCE_DELAY_MS);
  const activeSearch = useMemo(() => debouncedSearch.trim() || null, [debouncedSearch]);

  // Pagination state
  const [limit, setLimit] = useState(() => {
    const limitParam = searchParams.get('limit');
    return limitParam ? parseInt(limitParam, 10) : DEFAULT_LIMIT;
  });
  const [offset, setOffset] = useState(0);

  // Data state
  const [executions, setExecutions] = useState<TaskExecutionResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isFiltering, setIsFiltering] = useState(false);

  // Modal state
  const [modalState, setModalState] = useState<ModalState>({
    isOpen: false,
    title: '',
    message: '',
    type: 'info',
  });

  // Refs
  const isInitialMountRef = useRef(true);

  // Sync state to URL
  useUrlSync(searchParams, setSearchParams, activeSearch, limit);

  // Sync search input from URL (external changes like browser back/forward)
  // Use ref to track previous URL value to detect external changes
  const prevUrlSearchRef = useRef<string>(searchParams.get('search') || '');
  useEffect(() => {
    const urlSearch = searchParams.get('search') || '';

    // Only update if URL changed externally (not from our own updates)
    if (urlSearch !== prevUrlSearchRef.current && urlSearch !== debouncedSearch) {
      setSearchInput(urlSearch);
    }

    prevUrlSearchRef.current = urlSearch;
  }, [searchParams, debouncedSearch]);

  // Fetch executions
  const fetchExecutions = useCallback(async () => {
    if (isInitialMountRef.current) {
      setIsLoading(true);
      isInitialMountRef.current = false;
    } else {
      setIsFiltering(true);
    }

    try {
      const response = await api.SystemService.getTaskExecutionsApiV1SystemTaskExecutionsGet(
        activeSearch || undefined,
        limit,
        offset
      );

      setExecutions(response.executions);
      setTotal(response.total);
    } catch (error: unknown) {
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to fetch task executions';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      setModalState({
        isOpen: true,
        title: 'Error',
        message: errorDetail || errorMessage,
        type: 'error',
      });
    } finally {
      setIsLoading(false);
      setIsFiltering(false);
    }
  }, [activeSearch, limit, offset]);

  useEffect(() => {
    fetchExecutions();
  }, [fetchExecutions]);

  // Handlers
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchInput(e.target.value);
    setOffset(0);
  }, []);

  const handleResetSearch = useCallback(() => {
    setSearchInput('');
    setOffset(0);
  }, []);

  const handleLimitChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLimit = parseInt(e.target.value, 10);
    setLimit(newLimit);
    setOffset(0);
  }, []);

  const handlePageChange = useCallback((newOffset: number) => {
    setOffset(newOffset);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleViewDetails = useCallback(
    (execution: TaskExecutionResponse) => {
      navigate(`/task-executions/${execution.id}`);
    },
    [navigate]
  );

  const handleModalClose = useCallback(() => {
    setModalState((prev) => ({ ...prev, isOpen: false }));
  }, []);

  // Computed values
  const totalPages = useMemo(() => Math.ceil(total / limit), [total, limit]);
  const currentPage = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit]);
  const hasNextPage = offset + limit < total;
  const hasPreviousPage = offset > 0;

  // Render helpers
  const renderStatusBadge = useCallback((status: string) => {
    const color = STATUS_COLORS[status] || '#fff';
    return (
      <span
        className="px-2 inline-flex text-xs leading-5 font-semibold rounded"
        style={{
          backgroundColor: `${color}20`,
          border: `1px solid ${color}`,
          color: color,
        }}
      >
        {status}
      </span>
    );
  }, []);

  const renderExecutionRow = useCallback(
    (execution: TaskExecutionResponse) => (
      <tr
        key={execution.id}
        style={{ borderBottom: '1px solid #8b7355' }}
        className="hover:opacity-80"
      >
        <td className="px-6 py-4 whitespace-nowrap text-sm osrs-text">{execution.id}</td>
        <td className="px-6 py-4 text-sm osrs-text">
          <div className="max-w-xs truncate" title={execution.task_name}>
            {execution.task_name}
          </div>
        </td>
        <td className="px-6 py-4 whitespace-nowrap">{renderStatusBadge(execution.status)}</td>
        <td className="px-6 py-4 whitespace-nowrap text-sm osrs-text-secondary">
          {format(new Date(execution.started_at), 'MMM d, yyyy HH:mm:ss')}
        </td>
        <td className="px-6 py-4 whitespace-nowrap text-sm osrs-text-secondary">
          {execution.duration_seconds != null
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
    ),
    [renderStatusBadge, handleViewDetails]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="osrs-text text-xl">Loading task executions...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="osrs-card-title text-3xl">Task Executions</h1>
        {isFiltering && <div className="osrs-text-secondary text-sm">Filtering...</div>}
      </div>

      {/* Search */}
      <div className="osrs-card">
        <h2 className="osrs-card-title mb-4">Search</h2>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <input
              type="text"
              value={searchInput}
              onChange={handleSearchChange}
              placeholder="Search by task name, status, schedule ID, or player name..."
              className="osrs-btn w-full"
              style={{ backgroundColor: '#3a3024', color: '#ffd700' }}
            />
          </div>
          <button onClick={handleResetSearch} className="osrs-btn">
            Clear
          </button>
          <div className="flex items-center gap-2">
            <label className="text-sm osrs-text-secondary">Limit:</label>
            <select value={limit} onChange={handleLimitChange} className="osrs-btn">
              {LIMIT_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
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
                disabled={!hasPreviousPage}
                className="osrs-btn"
                style={{ opacity: hasPreviousPage ? 1 : 0.5 }}
              >
                Previous
              </button>
              <span className="osrs-text-secondary">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => handlePageChange(offset + limit)}
                disabled={!hasNextPage}
                className="osrs-btn"
                style={{ opacity: hasNextPage ? 1 : 0.5 }}
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
                {[
                  'ID',
                  'Task Name',
                  'Status',
                  'Started At',
                  'Duration',
                  'Retries',
                  'Actions',
                ].map((header) => (
                  <th
                    key={header}
                    className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase"
                    style={{ borderBottom: '2px solid #8b7355' }}
                  >
                    {header}
                  </th>
                ))}
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
                executions.map(renderExecutionRow)
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      <Modal
        isOpen={modalState.isOpen}
        onClose={handleModalClose}
        title={modalState.title}
        type={modalState.type}
        showConfirm={false}
      >
        {modalState.message}
      </Modal>
    </div>
  );
};
