import { useState } from 'react';
import type { ScheduledTaskInfo } from '../../api/models/ScheduledTaskInfo';
import { api } from '../../api/apiClient';
import { useNotificationContext } from '../../contexts/NotificationContext';
import { extractErrorMessage } from '../../utils/errorHandler';

interface ScheduledTasksTableProps {
  tasks: ScheduledTaskInfo[];
  onTaskTriggered?: () => void;
}

export const ScheduledTasksTable: React.FC<ScheduledTasksTableProps> = ({
  tasks,
  onTaskTriggered,
}) => {
  const { showNotification } = useNotificationContext();
  const [triggeringTask, setTriggeringTask] = useState<string | null>(null);

  // Helper function to format task names for display
  const formatTaskName = (name: string): string => {
    // Remove module prefix (e.g., "app.workers.maintenance:")
    const withoutModule = name.includes(':') ? name.split(':')[1] : name;
    // Replace underscores with spaces and capitalize words
    return withoutModule
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const handleTrigger = async (taskName: string) => {
    setTriggeringTask(taskName);
    try {
      await api.SystemService.triggerScheduledTaskApiV1SystemTriggerTaskTaskNamePost(taskName);
      const formattedName = formatTaskName(taskName);
      showNotification(`${formattedName} triggered successfully`, 'success');
      onTaskTriggered?.();
    } catch (error: unknown) {
      const formattedName = formatTaskName(taskName);
      const errorMessage = extractErrorMessage(error, `Failed to trigger task "${formattedName}"`);
      showNotification(errorMessage, 'error');
    } finally {
      setTriggeringTask(null);
    }
  };



  if (tasks.length === 0) {
    return (
      <div className="osrs-card p-8 text-center">
        <p className="text-secondary-600 dark:text-secondary-400">
          No scheduled tasks found.
        </p>
      </div>
    );
  }

  return (
    <div className="osrs-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-secondary-700 dark:text-secondary-300 uppercase tracking-wider">
                Task Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-secondary-700 dark:text-secondary-300 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-secondary-700 dark:text-secondary-300 uppercase tracking-wider">
                Cron Expression
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-secondary-700 dark:text-secondary-300 uppercase tracking-wider">
                Last Run
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-secondary-700 dark:text-secondary-300 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
            {tasks.map((task) => {
              const isTriggering = triggeringTask === task.name;

              return (
                <tr
                  key={task.name}
                  className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {task.friendly_name || task.name}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {task.description}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <code className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                      {task.cron_expression}
                    </code>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {task.last_run ? (
                        <span>{new Date(task.last_run).toLocaleString()}</span>
                      ) : (
                        <span className="text-secondary-500">Never</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleTrigger(task.name)}
                        disabled={isTriggering}
                        className="osrs-button-secondary text-xs px-3 py-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Trigger task now"
                      >
                        {isTriggering ? (
                          <span className="flex items-center gap-1">
                            <svg
                              className="w-4 h-4 animate-spin"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                              />
                            </svg>
                            Triggering...
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <svg
                              className="w-4 h-4"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                              />
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                              />
                            </svg>
                            Trigger
                          </span>
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

