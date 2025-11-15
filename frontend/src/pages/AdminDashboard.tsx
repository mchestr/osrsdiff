import { useEffect, useState } from 'react';
import { api } from '../api/apiClient';
import type { CostStatsResponse } from '../api/models/OpenAICostStatsResponse';
import type { TaskExecutionResponse } from '../api/models/TaskExecutionResponse';
import { Modal } from '../components/Modal';
import {
  SystemHealthStats,
  CostStatistics,
  TaskExecutionHealth,
  QuickActions,
  useExecutionSummary,
  type DatabaseStats,
  type SystemHealth,
} from '../components/admin';

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

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalMessage, setModalMessage] = useState<string | React.ReactNode>('');
  const [modalType, setModalType] = useState<'info' | 'error' | 'success' | 'warning'>('info');
  const [modalShowConfirm, setModalShowConfirm] = useState(false);
  const [modalConfirmCallback, setModalConfirmCallback] = useState<(() => void) | null>(null);

  useEffect(() => {
    fetchData();
    fetchExecutionSummary();
    fetchCosts();
  }, []);

  const fetchCosts = async () => {
    setCostsLoading(true);
    try {
      const response = await api.SystemService.getCostsApiV1SystemCostsGet();
      setCosts(response);
    } catch (error: unknown) {
      console.error('Failed to fetch costs:', error);
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
      console.error('Failed to fetch execution summary:', error);
    } finally {
      setSummaryLoading(false);
    }
  };


  const showModal = (
    title: string,
    message: string | React.ReactNode,
    type: 'info' | 'error' | 'success' | 'warning' = 'info'
  ) => {
    setModalTitle(title);
    setModalMessage(message);
    setModalType(type);
    setModalShowConfirm(false);
    setModalOpen(true);
  };

  const showConfirmModal = (
    title: string,
    message: string | React.ReactNode,
    onConfirm: () => void,
    type: 'info' | 'error' | 'success' | 'warning' = 'warning'
  ) => {
    setModalTitle(title);
    setModalMessage(message);
    setModalType(type);
    setModalShowConfirm(true);
    setModalConfirmCallback(() => onConfirm);
    setModalOpen(true);
  };

  const handleModalClose = () => {
    setModalOpen(false);
    setModalConfirmCallback(null);
  };

  const handleModalConfirm = () => {
    if (modalConfirmCallback) {
      modalConfirmCallback();
    }
    handleModalClose();
  };

  const fetchData = async () => {
    try {
      const [statsRes, healthRes] = await Promise.all([
        api.SystemService.getDatabaseStatsApiV1SystemStatsGet(),
        api.SystemService.getSystemHealthApiV1SystemHealthGet(),
      ]);

      setStats(statsRes);
      setHealth(healthRes);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };


  const handleVerifySchedules = async () => {
    setVerifyingSchedules(true);
    try {
      const response = await api.PlayersService.verifyAllSchedulesApiV1PlayersSchedulesVerifyPost();
      const message = (
        <div className="space-y-2">
          <p>Schedule verification completed.</p>
          <div className="space-y-1 text-sm">
            <p>Total schedules: <span className="font-bold">{response.total_schedules}</span></p>
            <p>Player fetch schedules: <span className="font-bold">{response.player_fetch_schedules}</span></p>
            <p>Invalid schedules: <span className="font-bold" style={{ color: response.invalid_schedules.length > 0 ? '#d32f2f' : '#4caf50' }}>{response.invalid_schedules.length}</span></p>
            <p>Orphaned schedules: <span className="font-bold" style={{ color: response.orphaned_schedules.length > 0 ? '#d32f2f' : '#4caf50' }}>{response.orphaned_schedules.length}</span></p>
            <p>Duplicate schedules: <span className="font-bold" style={{ color: Object.keys(response.duplicate_schedules).length > 0 ? '#d32f2f' : '#4caf50' }}>{Object.keys(response.duplicate_schedules).length}</span></p>
          </div>
        </div>
      );
      showModal('Schedule Verification', message, response.invalid_schedules.length > 0 || response.orphaned_schedules.length > 0 ? 'warning' : 'success');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to verify schedules';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
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
            <div className="space-y-2">
              <p>{response.message}</p>
              <div className="space-y-1 text-sm">
                <p>Tasks triggered: <span className="font-bold" style={{ color: '#4caf50' }}>{response.tasks_triggered}</span></p>
              </div>
            </div>
          );
          showModal('Summaries Generated', message, 'success');
        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to generate summaries';
          const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
          showModal('Error', errorDetail || errorMessage, 'error');
        } finally {
          setGeneratingSummaries(false);
        }
      },
      'info'
    );
  };


  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-secondary-700 text-xl">Loading dashboard...</div>
      </div>
    );
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

      {/* Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={handleModalClose}
        title={modalTitle}
        type={modalType}
        showConfirm={modalShowConfirm}
        onConfirm={handleModalConfirm}
      >
        {modalMessage}
      </Modal>
    </div>
  );
};

