import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import type { TaskExecutionResponse } from '../../api/models/TaskExecutionResponse';
import { TaskExecutionStatusBadge } from './TaskExecutionStatusBadge';

interface TaskExecutionRowProps {
  execution: TaskExecutionResponse;
}

export const TaskExecutionRow: React.FC<TaskExecutionRowProps> = ({
  execution,
}) => {
  return (
    <tr
      style={{ borderBottom: '1px solid #8b7355' }}
      className="hover:opacity-80"
    >
      <td className="px-6 py-4 whitespace-nowrap text-sm osrs-text">{execution.id}</td>
      <td className="px-6 py-4 text-sm osrs-text">
        <Link
          to={`/task-executions/${execution.id}`}
          className="max-w-xs truncate block hover:text-primary-500 dark:hover:text-primary-400 transition-colors"
          title={execution.task_name}
        >
          {execution.task_name}
        </Link>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <TaskExecutionStatusBadge status={execution.status} />
      </td>
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
    </tr>
  );
};

