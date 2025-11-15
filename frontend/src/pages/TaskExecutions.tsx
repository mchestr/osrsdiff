import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/apiClient';
import type { TaskExecutionResponse } from '../api/models/TaskExecutionResponse';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Modal } from '../components/Modal';
import {
  TaskExecutionPagination,
  TaskExecutionSearchBar,
  TaskExecutionTable,
  useDebounce,
  useUrlSync,
} from '../components/admin';
import { useModal } from '../hooks';
import { extractErrorMessage } from '../utils/errorHandler';

// Constants
const DEBOUNCE_DELAY_MS = 500;
const DEFAULT_LIMIT = 50;

// Component
export const TaskExecutions: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

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
  const { modalState, showModal, closeModal } = useModal();

  // Refs
  const isInitialMountRef = useRef(true);

  // Sync state to URL
  useUrlSync(searchParams, setSearchParams, activeSearch, limit, DEFAULT_LIMIT);

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
      const errorMessage = extractErrorMessage(error, 'Failed to fetch task executions');
      showModal('Error', errorMessage, 'error');
    } finally {
      setIsLoading(false);
      setIsFiltering(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Computed values
  const totalPages = useMemo(() => Math.ceil(total / limit), [total, limit]);
  const currentPage = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit]);
  const hasNextPage = offset + limit < total;
  const hasPreviousPage = offset > 0;


  if (isLoading) {
    return <LoadingSpinner message="Loading task executions..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="osrs-card-title text-3xl">Task Executions</h1>
      </div>

      {/* Search */}
      <TaskExecutionSearchBar
        searchInput={searchInput}
        onSearchChange={handleSearchChange}
        onResetSearch={handleResetSearch}
        limit={limit}
        onLimitChange={handleLimitChange}
        isFiltering={isFiltering}
      />

      {/* Pagination */}
      <TaskExecutionPagination
        currentPage={currentPage}
        totalPages={totalPages}
        hasPreviousPage={hasPreviousPage}
        hasNextPage={hasNextPage}
        onPageChange={handlePageChange}
        offset={offset}
        limit={limit}
      />

      {/* Executions Table */}
      <TaskExecutionTable
        executions={executions}
      />

      {/* Modal */}
      <Modal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        title={modalState.title}
        type={modalState.type}
        showConfirm={false}
      >
        {modalState.message}
      </Modal>
    </div>
  );
};
