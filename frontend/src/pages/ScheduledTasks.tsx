import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/apiClient';
import type { ScheduledTaskInfo } from '../api/models/ScheduledTaskInfo';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ScheduledTasksTable } from '../components/admin/ScheduledTasksTable';
import { useNotificationContext } from '../contexts/NotificationContext';
import { extractErrorMessage } from '../utils/errorHandler';

export const ScheduledTasks: React.FC = () => {
  const [tasks, setTasks] = useState<ScheduledTaskInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isTriggerDropdownOpen, setIsTriggerDropdownOpen] = useState(false);
  const [triggeringScheduleId, setTriggeringScheduleId] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { showNotification } = useNotificationContext();

  // Helper function to format task names for display
  const formatTaskName = useCallback((name: string): string => {
    // Remove module prefix (e.g., "app.workers.maintenance:")
    const withoutModule = name.includes(':') ? name.split(':')[1] : name;
    // Replace underscores with spaces and capitalize words
    return withoutModule
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }, []);

  const fetchTasks = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    try {
      const response = await api.SystemService.getScheduledTasksApiV1SystemScheduledTasksGet();
      setTasks(response.tasks);
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to fetch scheduled tasks');
      showNotification(errorMessage, 'error');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [showNotification]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsTriggerDropdownOpen(false);
      }
    };

    if (isTriggerDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isTriggerDropdownOpen]);

  const handleRefresh = useCallback(() => {
    fetchTasks(true);
  }, [fetchTasks]);

  const handleTaskTriggered = useCallback(() => {
    // Refresh tasks after a short delay to see updated status
    // Note: Notification is already shown in handleTriggerFromDropdown
    setTimeout(() => {
      fetchTasks(true);
    }, 1000);
  }, [fetchTasks]);

  const handleTriggerFromDropdown = useCallback(async (scheduleId: string) => {
    setIsTriggerDropdownOpen(false);
    setTriggeringScheduleId(scheduleId);
    try {
      await api.SystemService.triggerScheduledTaskApiV1SystemTriggerTaskTaskNamePost(scheduleId);
      // Find the task to get its friendly name
      const task = tasks.find(t => t.name === scheduleId);
      const displayName = task?.friendly_name || formatTaskName(scheduleId);
      showNotification(`${displayName} triggered successfully`, 'success');
      handleTaskTriggered();
    } catch (error: unknown) {
      const task = tasks.find(t => t.name === scheduleId);
      const displayName = task?.friendly_name || formatTaskName(scheduleId);
      const errorMessage = extractErrorMessage(error, `Failed to trigger task "${displayName}"`);
      showNotification(errorMessage, 'error');
    } finally {
      setTriggeringScheduleId(null);
    }
  }, [showNotification, handleTaskTriggered, formatTaskName, tasks]);

  // Use tasks directly from API response, filtering out player-specific tasks that require arguments
  // and tasks without schedules (cron_expression === "N/A")
  const triggerableTasks = tasks
    .filter(task =>
      !task.name.startsWith('player_fetch_') &&
      task.cron_expression !== "N/A"
    )
    .sort((a, b) => a.name.localeCompare(b.name));



  if (isLoading) {
    return <LoadingSpinner message="Loading scheduled tasks..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="osrs-card-title text-3xl">Scheduled Tasks</h1>
        <div className="flex items-center gap-3">
          {/* Trigger Tasks Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setIsTriggerDropdownOpen(!isTriggerDropdownOpen)}
              disabled={isRefreshing}
              className="osrs-button-secondary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Trigger a scheduled task or validate schedules"
            >
              <svg
                className="w-5 h-5"
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
              Trigger Task
              <svg
                className={`w-4 h-4 transition-transform ${isTriggerDropdownOpen ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
            {isTriggerDropdownOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-50 max-h-96 overflow-y-auto">
                <div className="p-2">
                  <div className="px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Select Task to Trigger
                  </div>
                  {triggerableTasks.length > 0 && (
                    <>
                      <div className="my-1 border-t border-gray-200 dark:border-gray-700" />
                      {triggerableTasks.map((task) => {
                        const isTriggering = triggeringScheduleId === task.name;
                        const displayName = task.friendly_name || task.name;

                        return (
                          <button
                            key={task.name}
                            onClick={() => handleTriggerFromDropdown(task.name)}
                            disabled={isTriggering}
                            className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-between"
                          >
                            <div className="flex-1 min-w-0 pr-2">
                              <div className="font-medium break-words">{displayName}</div>
                              <div className="text-xs text-gray-500 dark:text-gray-400 break-words mt-0.5">
                                {task.description}
                              </div>
                            </div>
                            {isTriggering && (
                              <svg
                                className="w-4 h-4 animate-spin ml-2 flex-shrink-0"
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
                            )}
                          </button>
                        );
                      })}
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="osrs-button-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg
              className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`}
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
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Tasks Table */}
      <ScheduledTasksTable
        tasks={tasks}
        onTaskTriggered={handleTaskTriggered}
      />
    </div>
  );
};

