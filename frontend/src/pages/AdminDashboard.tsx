import { useEffect, useState } from 'react';
import { api } from '../api/apiClient';
import type { CostStatsResponse } from '../api/models/OpenAICostStatsResponse';
import type { TaskExecutionResponse } from '../api/models/TaskExecutionResponse';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Modal } from '../components/Modal';
import {
  CostStatistics,
  QuickActions,
  SystemHealthStats,
  TaskExecutionHealth,
  useExecutionSummary,
  type DatabaseStats,
  type SystemHealth,
} from '../components/admin';
import { useNotificationContext } from '../contexts/NotificationContext';
import { useModal } from '../hooks';
import { extractErrorMessage } from '../utils/errorHandler';

export const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifyingSchedules, setVerifyingSchedules] = useState(false);
  const [generatingSummaries, setGeneratingSummaries] = useState(false);


  // Task execution summary state
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [executionsForGraph, setExecutionsForGraph] = useState<TaskExecutionResponse[]>([]);
  const [executionTotal, setExecutionTotal] = useState(0);

  // Calculate execution summary using hook
  const executionSummary = useExecutionSummary(executionsForGraph, executionTotal);

  // Cost stats state
  const [costs, setCosts] = useState<CostStatsResponse | null>(null);
  const [costsLoading, setCostsLoading] = useState(false);

  // Modal state (for confirmations only)
  const { modalState, showConfirmModal, closeModal, handleConfirm } = useModal();
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


  const handleVerifySchedules = async () => {
    setVerifyingSchedules(true);
    try {
      const response = await api.PlayersService.verifyAllSchedulesApiV1PlayersSchedulesVerifyPost();
      const hasIssues = response.invalid_schedules.length > 0 || response.orphaned_schedules.length > 0;
      const message = (
        <div className="space-y-1">
          <p>Schedule verification completed.</p>
          <div className="space-y-1 text-sm">
            <p>Total schedules: <span className="font-bold">{response.total_schedules}</span></p>
            <p>Player fetch schedules: <span className="font-bold">{response.player_fetch_schedules}</span></p>
            <p>Invalid schedules: <span className={`font-bold ${response.invalid_schedules.length > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>{response.invalid_schedules.length}</span></p>
            <p>Orphaned schedules: <span className={`font-bold ${response.orphaned_schedules.length > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>{response.orphaned_schedules.length}</span></p>
            <p>Duplicate schedules: <span className={`font-bold ${Object.keys(response.duplicate_schedules).length > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>{Object.keys(response.duplicate_schedules).length}</span></p>
          </div>
        </div>
      );
      showNotification(message, hasIssues ? 'warning' : 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to verify schedules');
      showNotification(errorMessage, 'error');
    } finally {
      setVerifyingSchedules(false);
    }
  };

  const handleGenerateSummaries = async () => {
    showConfirmModal(
      'Generate Summaries',
      'Generate summaries for all active players? This will trigger AI-powered summary generation tasks.',
      async () => {
        setGeneratingSummaries(true);
        try {
          const response = await api.SystemService.generateSummariesApiV1SystemGenerateSummariesPost({
            player_id: null,
            force_regenerate: false,
          });

          const message = (
            <div className="space-y-1">
              <p>{response.message}</p>
              <div className="space-y-1 text-sm">
                <p>Tasks triggered: <span className="font-bold text-green-600 dark:text-green-400">{response.tasks_triggered}</span></p>
              </div>
            </div>
          );
          showNotification(message, 'success');
        } catch (error: unknown) {
          const errorMessage = extractErrorMessage(error, 'Failed to generate summaries');
          showNotification(errorMessage, 'error');
        } finally {
          setGeneratingSummaries(false);
        }
      },
      'info'
    );
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

      {/* Quick Actions */}
      <QuickActions
        onVerifySchedules={handleVerifySchedules}
        onGenerateSummaries={handleGenerateSummaries}
        verifyingSchedules={verifyingSchedules}
        generatingSummaries={generatingSummaries}
      />

      {/* Confirmation Modal */}
      <Modal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        title={modalState.title}
        type={modalState.type}
        showConfirm={modalState.showConfirm}
        onConfirm={handleConfirm}
      >
        {modalState.message}
      </Modal>
    </div>
  );
};

