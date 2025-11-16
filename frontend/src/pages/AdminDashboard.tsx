import { useEffect, useState } from 'react';
import { api } from '../api/apiClient';
import type { CostStatsResponse } from '../api/models/OpenAICostStatsResponse';
import type { TaskExecutionResponse } from '../api/models/TaskExecutionResponse';
import { LoadingSpinner } from '../components/LoadingSpinner';
import {
  CostStatistics,
  SystemHealthStats,
  TaskExecutionHealth,
  useExecutionSummary,
  type DatabaseStats,
  type SystemHealth,
} from '../components/admin';
import { useNotificationContext } from '../contexts/NotificationContext';
import { extractErrorMessage } from '../utils/errorHandler';

export const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);


  // Task execution summary state
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [executionsForGraph, setExecutionsForGraph] = useState<TaskExecutionResponse[]>([]);
  const [executionTotal, setExecutionTotal] = useState(0);

  // Calculate execution summary using hook
  const executionSummary = useExecutionSummary(executionsForGraph, executionTotal);

  // Cost stats state
  const [costs, setCosts] = useState<CostStatsResponse | null>(null);
  const [costsLoading, setCostsLoading] = useState(false);

  const { showNotification } = useNotificationContext();

  useEffect(() => {
    fetchData();
    fetchExecutionSummary();
    fetchCosts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchCosts = async () => {
    setCostsLoading(true);
    try {
      const response = await api.SystemService.getCostsApiV1SystemCostsGet();
      setCosts(response);
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to fetch costs');
      showNotification(errorMessage, 'error');
    } finally {
      setCostsLoading(false);
    }
  };

  const fetchExecutionSummary = async () => {
    setSummaryLoading(true);
    try {
      // Fetch recent executions for summary (last 1000 to get good stats)
      const response = await api.SystemService.getTaskExecutionsApiV1SystemTaskExecutionsGet(
        null,
        1000,
        0
      );

      setExecutionsForGraph(response.executions);
      setExecutionTotal(response.total);
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to fetch execution summary');
      showNotification(errorMessage, 'error');
    } finally {
      setSummaryLoading(false);
    }
  };



  const fetchData = async () => {
    try {
      const [statsRes, healthRes] = await Promise.all([
        api.SystemService.getDatabaseStatsApiV1SystemStatsGet(),
        api.SystemService.getSystemHealthApiV1SystemHealthGet(),
      ]);

      setStats(statsRes);
      setHealth(healthRes);
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to fetch dashboard data');
      showNotification(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };





  if (loading) {
    return <LoadingSpinner message="Loading dashboard..." />;
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      <h1 className="osrs-card-title text-3xl sm:text-4xl mb-0">Admin Dashboard</h1>

      {/* System Health & Database Stats */}
      <SystemHealthStats health={health} stats={stats} />

      {/* Cost Statistics */}
      <CostStatistics costs={costs} loading={costsLoading} />

      {/* Task Execution Health Summary */}
      <TaskExecutionHealth
        executionSummary={executionSummary}
        executionsForGraph={executionsForGraph}
        loading={summaryLoading}
      />


    </div>
  );
};

