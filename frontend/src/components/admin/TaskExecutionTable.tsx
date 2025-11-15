import type { TaskExecutionResponse } from '../../api/models/TaskExecutionResponse';
import { TaskExecutionRow } from './TaskExecutionRow';

interface TaskExecutionTableProps {
  executions: TaskExecutionResponse[];
}

const TABLE_HEADERS = ['ID', 'Task Name', 'Status', 'Started At', 'Duration', 'Retries'] as const;

export const TaskExecutionTable: React.FC<TaskExecutionTableProps> = ({
  executions,
}) => {
  return (
    <div className="osrs-card">
      <div className="overflow-x-auto">
        <table className="min-w-full" style={{ borderCollapse: 'separate', borderSpacing: 0 }}>
          <thead>
            <tr className="bg-secondary-200 dark:bg-secondary-800">
              {TABLE_HEADERS.map((header) => (
                <th
                  key={header}
                  className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase border-b-2 border-secondary-700 dark:border-secondary-600"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {executions.length === 0 ? (
              <tr>
                <td colSpan={TABLE_HEADERS.length} className="px-6 py-8 text-center osrs-text-secondary">
                  No task executions found
                </td>
              </tr>
            ) : (
              executions.map((execution) => (
                <TaskExecutionRow
                  key={execution.id}
                  execution={execution}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

