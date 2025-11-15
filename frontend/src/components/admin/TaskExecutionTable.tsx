import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import type { TaskExecutionResponse } from '../../api/models/TaskExecutionResponse';
import { DataTable, type Column, type PaginationProps } from '../common';
import { TaskExecutionStatusBadge } from './TaskExecutionStatusBadge';

const LIMIT_OPTIONS = [25, 50, 100, 200] as const;

interface TaskExecutionTableProps {
  executions: TaskExecutionResponse[];
  searchInput: string;
  onSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onResetSearch: () => void;
  limit: number;
  onLimitChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  isFiltering?: boolean;
  pagination?: PaginationProps;
}

export const TaskExecutionTable: React.FC<TaskExecutionTableProps> = ({
  executions,
  searchInput,
  onSearchChange,
  onResetSearch,
  limit,
  onLimitChange,
  isFiltering = false,
  pagination,
}) => {
  const columns: Column<TaskExecutionResponse>[] = [
    {
      key: 'id',
      label: 'ID',
      sortable: true,
      className: 'whitespace-nowrap',
    },
    {
      key: 'task_name',
      label: 'Task Name',
      sortable: true,
      render: (execution) => (
        <Link
          to={`/task-executions/${execution.id}`}
          className="max-w-xs truncate block hover:text-primary-500 dark:hover:text-primary-400 transition-colors"
          title={execution.task_name}
          onClick={(e) => e.stopPropagation()}
        >
          {execution.task_name}
        </Link>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (execution) => <TaskExecutionStatusBadge status={execution.status} />,
      className: 'whitespace-nowrap',
    },
    {
      key: 'started_at',
      label: 'Started At',
      sortable: true,
      sortFn: (a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime(),
      render: (execution) => (
        <span className="whitespace-nowrap">
          {format(new Date(execution.started_at), 'MMM d, yyyy HH:mm:ss')}
        </span>
      ),
      className: 'whitespace-nowrap',
    },
    {
      key: 'duration_seconds',
      label: 'Duration',
      sortable: true,
      sortFn: (a, b) => {
        const aVal = a.duration_seconds ?? Infinity;
        const bVal = b.duration_seconds ?? Infinity;
        return aVal - bVal;
      },
      render: (execution) => (
        <span className="whitespace-nowrap">
          {execution.duration_seconds != null
            ? `${execution.duration_seconds.toFixed(3)}s`
            : '-'}
        </span>
      ),
      className: 'whitespace-nowrap',
    },
    {
      key: 'retry_count',
      label: 'Retries',
      sortable: true,
      render: (execution) => execution.retry_count,
      className: 'whitespace-nowrap',
    },
  ];

  return (
    <DataTable
      data={executions}
      columns={columns}
      keyExtractor={(execution) => execution.id}
      emptyMessage="No task executions found"
      searchable={{
        placeholder: 'Search by task name, status, schedule ID, or player name...',
        value: searchInput,
        onChange: (value) => {
          // Create synthetic event for compatibility
          const event = {
            target: { value },
            currentTarget: { value },
          } as React.ChangeEvent<HTMLInputElement>;
          onSearchChange(event);
        },
        onReset: onResetSearch,
        showClearButton: true,
        isFiltering,
      }}
      limitConfig={{
        value: limit,
        onChange: (newLimit) => {
          // Create synthetic event for compatibility
          const event = {
            target: { value: newLimit.toString() },
            currentTarget: { value: newLimit.toString() },
          } as React.ChangeEvent<HTMLSelectElement>;
          onLimitChange(event);
        },
        options: [...LIMIT_OPTIONS],
      }}
      pagination={pagination}
      showResultsCount={false}
    />
  );
};

