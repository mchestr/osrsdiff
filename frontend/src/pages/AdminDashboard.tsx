import { format } from 'date-fns';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api/apiClient';
import type { CostStatsResponse } from '../api/models/OpenAICostStatsResponse';
import type { TaskExecutionResponse } from '../api/models/TaskExecutionResponse';
import { Modal } from '../components/Modal';

interface Player {
  id: number;
  username: string;
  created_at: string;
  last_fetched: string | null;
  is_active: boolean;
  fetch_interval_minutes: number;
  schedule_id: string | null;
}

interface DatabaseStats {
  total_players: number;
  active_players: number;
  inactive_players: number;
  total_hiscore_records: number;
  oldest_record: string | null;
  newest_record: string | null;
  records_last_24h: number;
  records_last_7d: number;
  avg_records_per_player: number;
}

interface SystemHealth {
  status: string;
  database_connected: boolean;
  total_storage_mb: number | null;
  uptime_info: Record<string, unknown>;
}

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
};

// Helper function to format large numbers
const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
};

export const AdminDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [players, setPlayers] = useState<Player[]>([]);
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [newPlayerUsername, setNewPlayerUsername] = useState('');
  const [addingPlayer, setAddingPlayer] = useState(false);
  const [editingInterval, setEditingInterval] = useState<number | null>(null);
  const [intervalValue, setIntervalValue] = useState<string>('');
  const [verifyingSchedules, setVerifyingSchedules] = useState(false);
  const [fetchingAllPlayers, setFetchingAllPlayers] = useState(false);
  const [generatingSummaries, setGeneratingSummaries] = useState(false);


  // Task execution summary state
  const [executionSummary, setExecutionSummary] = useState<{
    total: number;
    successCount: number;
    failureCount: number;
    retryCount: number;
    pendingCount: number;
    successRate: number;
    failureRate: number;
    avgDuration: number;
    recentFailures24h: number;
    recentFailures7d: number;
    statusBreakdown: Record<string, number>;
  } | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [executionsForGraph, setExecutionsForGraph] = useState<TaskExecutionResponse[]>([]);

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

      const allExecutions = response.executions;
      setExecutionsForGraph(allExecutions);
      const now = new Date();
      const last24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      const last7d = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

      // Calculate statistics
      const total = response.total;
      const successCount = allExecutions.filter(e => e.status === 'success').length;
      const failureCount = allExecutions.filter(e => e.status === 'failure').length;
      const retryCount = allExecutions.filter(e => e.status === 'retry').length;
      const pendingCount = allExecutions.filter(e => e.status === 'pending').length;

      const successRate = total > 0 ? (successCount / total) * 100 : 0;
      const failureRate = total > 0 ? (failureCount / total) * 100 : 0;

      // Calculate average duration from completed executions
      const completedExecutions = allExecutions.filter(
        e => e.duration_seconds !== null && e.duration_seconds !== undefined
      );
      const avgDuration = completedExecutions.length > 0
        ? completedExecutions.reduce((sum, e) => sum + (e.duration_seconds || 0), 0) / completedExecutions.length
        : 0;

      // Count recent failures
      const recentFailures24h = allExecutions.filter(
        e => e.status === 'failure' && new Date(e.started_at) >= last24h
      ).length;
      const recentFailures7d = allExecutions.filter(
        e => e.status === 'failure' && new Date(e.started_at) >= last7d
      ).length;

      // Status breakdown
      const statusBreakdown: Record<string, number> = {};
      allExecutions.forEach(e => {
        statusBreakdown[e.status] = (statusBreakdown[e.status] || 0) + 1;
      });

      setExecutionSummary({
        total,
        successCount,
        failureCount,
        retryCount,
        pendingCount,
        successRate,
        failureRate,
        avgDuration,
        recentFailures24h,
        recentFailures7d,
        statusBreakdown,
      });
    } catch (error: unknown) {
      console.error('Failed to fetch execution summary:', error);
    } finally {
      setSummaryLoading(false);
    }
  };

  // Calculate time-series data for executions over time
  const timeSeriesData = useMemo(() => {
    if (executionsForGraph.length === 0) return [];

    // Sort executions by started_at
    const sorted = [...executionsForGraph].sort((a, b) =>
      new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
    );

    // Determine time grouping based on data range
    const firstTime = new Date(sorted[0].started_at).getTime();
    const lastTime = new Date(sorted[sorted.length - 1].started_at).getTime();
    const timeRange = lastTime - firstTime;
    const daysRange = timeRange / (1000 * 60 * 60 * 24);

    // Group by hour if less than 7 days, otherwise by day
    const groupByHour = daysRange < 7;

    // Create time buckets
    const timeBuckets: Record<string, { time: string; total: number; success: number; failure: number; retry: number; other: number }> = {};

    sorted.forEach((execution) => {
      const date = new Date(execution.started_at);
      let bucketKey: string;

      if (groupByHour) {
        // Group by hour - use more compact format
        bucketKey = format(date, 'MMM d HH:mm');
      } else {
        // Group by day - use more compact format
        bucketKey = format(date, 'MMM d');
      }

      if (!timeBuckets[bucketKey]) {
        timeBuckets[bucketKey] = {
          time: bucketKey,
          total: 0,
          success: 0,
          failure: 0,
          retry: 0,
          other: 0,
        };
      }

      timeBuckets[bucketKey].total++;
      const status = execution.status || 'unknown';
      if (status === 'success') {
        timeBuckets[bucketKey].success++;
      } else if (status === 'failure') {
        timeBuckets[bucketKey].failure++;
      } else if (status === 'retry') {
        timeBuckets[bucketKey].retry++;
      } else {
        timeBuckets[bucketKey].other++;
      }
    });

    return Object.values(timeBuckets);
  }, [executionsForGraph]);

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
      const [playersRes, statsRes, healthRes] = await Promise.all([
        api.PlayersService.listPlayersApiV1PlayersGet(false),
        api.SystemService.getDatabaseStatsApiV1SystemStatsGet(),
        api.SystemService.getSystemHealthApiV1SystemHealthGet(),
      ]);

      setPlayers(playersRes.players);
      setStats(statsRes);
      setHealth(healthRes);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPlayer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlayerUsername.trim()) return;

    setAddingPlayer(true);
    try {
      await api.PlayersService.addPlayerApiV1PlayersPost({
        username: newPlayerUsername.trim(),
      });
      setNewPlayerUsername('');
      await fetchData();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to add player';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
    } finally {
      setAddingPlayer(false);
    }
  };

  const handleToggleActive = async (username: string, isActive: boolean) => {
    try {
      if (isActive) {
        await api.PlayersService.deactivatePlayerApiV1PlayersUsernameDeactivatePost(username);
      } else {
        await api.PlayersService.reactivatePlayerApiV1PlayersUsernameReactivatePost(username);
      }
      await fetchData();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update player';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
    }
  };

  const handleDeletePlayer = async (username: string) => {
    showConfirmModal(
      'Delete Player',
      `Are you sure you want to delete player "${username}"? This action cannot be undone.`,
      async () => {
        try {
          await api.PlayersService.removePlayerApiV1PlayersUsernameDelete(username);
          await fetchData();
          showModal('Success', `Player "${username}" has been deleted.`, 'success');
        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to delete player';
          const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
          showModal('Error', errorDetail || errorMessage, 'error');
        }
      },
      'warning'
    );
  };

  const handleTriggerFetch = async (username: string) => {
    try {
      await api.PlayersService.triggerManualFetchApiV1PlayersUsernameFetchPost(username);
      showModal('Success', 'Fetch task enqueued successfully', 'success');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to trigger fetch';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
    }
  };

  const handleStartEditInterval = (playerId: number, currentInterval: number) => {
    setEditingInterval(playerId);
    setIntervalValue(currentInterval.toString());
  };

  const handleCancelEditInterval = () => {
    setEditingInterval(null);
    setIntervalValue('');
  };

  const handleSaveInterval = async (username: string) => {
    const newInterval = parseInt(intervalValue, 10);
    if (isNaN(newInterval) || newInterval < 1 || newInterval > 10080) {
      showModal('Invalid Interval', 'Interval must be between 1 and 10080 minutes (1 week)', 'error');
      return;
    }

    try {
      await api.PlayersService.updatePlayerFetchIntervalApiV1PlayersUsernameFetchIntervalPut(
        username,
        { fetch_interval_minutes: newInterval }
      );
      setEditingInterval(null);
      setIntervalValue('');
      await fetchData();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update interval';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
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

  const handleFetchAllPlayers = async () => {
    const activePlayers = players.filter((p) => p.is_active);
    if (activePlayers.length === 0) {
      showModal('No Active Players', 'No active players to fetch', 'info');
      return;
    }

    showConfirmModal(
      'Fetch All Active Players',
      `Trigger fetch for all ${activePlayers.length} active players?`,
      async () => {
        setFetchingAllPlayers(true);
        try {
          let successCount = 0;
          let errorCount = 0;

          // Trigger fetch for each active player
          for (const player of activePlayers) {
            try {
              await api.PlayersService.triggerManualFetchApiV1PlayersUsernameFetchPost(player.username);
              successCount++;
            } catch (error) {
              errorCount++;
              console.error(`Failed to trigger fetch for ${player.username}:`, error);
            }
          }

          const message = (
            <div className="space-y-2">
              <p>Fetch tasks triggered:</p>
              <div className="space-y-1 text-sm">
                <p>Success: <span className="font-bold" style={{ color: '#4caf50' }}>{successCount}</span></p>
                <p>Errors: <span className="font-bold" style={{ color: errorCount > 0 ? '#d32f2f' : '#4caf50' }}>{errorCount}</span></p>
              </div>
            </div>
          );
          showModal('Fetch Complete', message, errorCount > 0 ? 'warning' : 'success');
        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to trigger fetches';
          showModal('Error', errorMessage, 'error');
        } finally {
          setFetchingAllPlayers(false);
        }
      },
      'info'
    );
  };

  const handleGenerateSummaries = async () => {
    const activePlayers = players.filter((p) => p.is_active);
    if (activePlayers.length === 0) {
      showModal('No Active Players', 'No active players to generate summaries for', 'info');
      return;
    }

    showConfirmModal(
      'Generate Summaries',
      `Generate summaries for all ${activePlayers.length} active players? This will trigger AI-powered summary generation tasks.`,
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
        <div className="osrs-text text-xl">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="osrs-card-title text-3xl">Admin Dashboard</h1>

      {/* System Health & Database Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-7 gap-6">
        {health && (
          <>
            <div className="osrs-card">
              <h3 className="osrs-stat-label mb-2">System Status</h3>
              <div className="flex items-center justify-center">
                <span
                  className="text-4xl"
                  style={{ color: health.status === 'healthy' ? '#4caf50' : '#d32f2f' }}
                  title={health.status.toUpperCase()}
                >
                  {health.status === 'healthy' ? '✓' : '✗'}
                </span>
              </div>
            </div>
            <div className="osrs-card">
              <h3 className="osrs-stat-label mb-2">Database</h3>
              <div className="flex items-center justify-center">
                <span
                  className="text-4xl"
                  style={{ color: health.database_connected ? '#4caf50' : '#d32f2f' }}
                  title={health.database_connected ? 'Connected' : 'Disconnected'}
                >
                  {health.database_connected ? '✓' : '✗'}
                </span>
              </div>
            </div>
            {health.total_storage_mb && (
              <div className="osrs-card">
                <h3 className="osrs-stat-label mb-2">Storage</h3>
                <p className="osrs-stat-value" title={`${health.total_storage_mb.toFixed(2)} MB`}>
                  {formatNumber(Math.round(health.total_storage_mb))} MB
                </p>
              </div>
            )}
          </>
        )}
        {stats && (
          <>
            <div className="osrs-card">
              <h3 className="osrs-stat-label mb-2">Total Players</h3>
              <p className="osrs-stat-value" title={stats.total_players.toString()}>
                {formatNumber(stats.total_players)}
              </p>
            </div>
            <div className="osrs-card">
              <h3 className="osrs-stat-label mb-2">Active Players</h3>
              <p className="osrs-stat-value" style={{ color: '#ffd700' }} title={stats.active_players.toString()}>
                {formatNumber(stats.active_players)}
              </p>
            </div>
            <div className="osrs-card">
              <h3 className="osrs-stat-label mb-2">Total Records</h3>
              <p className="osrs-stat-value" title={stats.total_hiscore_records.toLocaleString()}>
                {formatNumber(stats.total_hiscore_records)}
              </p>
            </div>
            <div className="osrs-card">
              <h3 className="osrs-stat-label mb-2">Records (24h)</h3>
              <p className="osrs-stat-value" title={stats.records_last_24h.toString()}>
                {formatNumber(stats.records_last_24h)}
              </p>
            </div>
          </>
        )}
      </div>

      {/* Cost Statistics */}
      <div className="osrs-card">
        <h2 className="osrs-card-title mb-4">Cost Statistics</h2>
        {costsLoading ? (
          <div className="flex items-center justify-center py-4">
            <div className="osrs-text-secondary">Loading cost statistics...</div>
          </div>
        ) : costs ? (
          <div className="space-y-4">
            {/* Cost Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="osrs-card" style={{ backgroundColor: '#2d2418', border: '1px solid #8b7355' }}>
                <h3 className="osrs-stat-label mb-2">Total Cost</h3>
                <p className="osrs-stat-value" style={{ color: '#ffd700', fontSize: '1.5rem' }}>
                  ${costs.total_cost_usd.toFixed(4)}
                </p>
              </div>
              <div className="osrs-card" style={{ backgroundColor: '#2d2418', border: '1px solid #8b7355' }}>
                <h3 className="osrs-stat-label mb-2">Last 24 Hours</h3>
                <p className="osrs-stat-value" style={{ color: '#4caf50', fontSize: '1.5rem' }}>
                  ${costs.cost_last_24h_usd.toFixed(4)}
                </p>
              </div>
              <div className="osrs-card" style={{ backgroundColor: '#2d2418', border: '1px solid #8b7355' }}>
                <h3 className="osrs-stat-label mb-2">Last 7 Days</h3>
                <p className="osrs-stat-value" style={{ color: '#4caf50', fontSize: '1.5rem' }}>
                  ${costs.cost_last_7d_usd.toFixed(4)}
                </p>
              </div>
              <div className="osrs-card" style={{ backgroundColor: '#2d2418', border: '1px solid #8b7355' }}>
                <h3 className="osrs-stat-label mb-2">Last 30 Days</h3>
                <p className="osrs-stat-value" style={{ color: '#4caf50', fontSize: '1.5rem' }}>
                  ${costs.cost_last_30d_usd.toFixed(4)}
                </p>
              </div>
            </div>

            {/* Token Usage Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t" style={{ borderColor: '#8b7355' }}>
              <div>
                <h3 className="osrs-stat-label mb-1">Total Summaries</h3>
                <p className="osrs-stat-value">{costs.total_summaries.toLocaleString()}</p>
              </div>
              <div>
                <h3 className="osrs-stat-label mb-1">Total Tokens</h3>
                <p className="osrs-stat-value">{formatNumber(costs.total_tokens)}</p>
                <p className="text-xs osrs-text-secondary mt-1">
                  {formatNumber(costs.total_prompt_tokens)} prompt + {formatNumber(costs.total_completion_tokens)} completion
                </p>
              </div>
              <div>
                <h3 className="osrs-stat-label mb-1">Avg Cost per Summary</h3>
                <p className="osrs-stat-value">
                  {costs.total_summaries > 0
                    ? `$${(costs.total_cost_usd / costs.total_summaries).toFixed(6)}`
                    : '$0.000000'}
                </p>
              </div>
            </div>

            {/* Model Breakdown */}
            {Object.keys(costs.by_model).length > 0 && (
              <div className="pt-2 border-t" style={{ borderColor: '#8b7355' }}>
                <h3 className="osrs-stat-label mb-3">Cost Breakdown by Model</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {Object.entries(costs.by_model).map(([model, stats]) => (
                    <div
                      key={model}
                      className="p-3 rounded"
                      style={{
                        backgroundColor: '#1a1510',
                        border: '1px solid #8b7355',
                      }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold osrs-text" style={{ color: '#ffd700' }}>
                          {model}
                        </span>
                        <span className="text-sm osrs-text-secondary">
                          {stats.count} summaries
                        </span>
                      </div>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="osrs-text-secondary">Cost:</span>
                          <span className="osrs-text" style={{ color: '#4caf50' }}>
                            ${stats.cost_usd.toFixed(4)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="osrs-text-secondary">Tokens:</span>
                          <span className="osrs-text">{formatNumber(stats.total_tokens)}</span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="osrs-text-secondary">Avg per summary:</span>
                          <span className="osrs-text-secondary">
                            ${stats.count > 0 ? (stats.cost_usd / stats.count).toFixed(6) : '0.000000'}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center py-4">
            <div className="osrs-text-secondary">No cost data available</div>
          </div>
        )}
      </div>

      {/* Task Execution Health Summary */}
      <div className="osrs-card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="osrs-card-title mb-0">Task Execution Health</h2>
          <Link
            to="/task-executions"
            className="osrs-btn text-sm"
            style={{ minWidth: 'auto', padding: '0.5rem 1rem' }}
          >
            View All →
          </Link>
        </div>
        {summaryLoading ? (
          <div className="flex items-center justify-center py-4">
            <div className="osrs-text-secondary">Loading summary...</div>
          </div>
        ) : executionSummary ? (
          <div className="space-y-4">
            {/* Task Executions Over Time Graph */}
            {executionsForGraph.length > 0 && timeSeriesData.length > 0 && (
              <div className="pb-4 border-b" style={{ borderColor: '#8b7355' }}>
                <h3 className="osrs-stat-label mb-4">Task Executions Over Time</h3>
                <div className="h-96" style={{ backgroundColor: '#1d1611' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={timeSeriesData} margin={{ top: 10, right: 30, left: 20, bottom: 60 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#8b7355" opacity={0.3} />
                      <XAxis
                        dataKey="time"
                        angle={-45}
                        textAnchor="end"
                        height={60}
                        tick={{ fontSize: 9, fill: '#ffd700', fontFamily: 'Courier New, Courier, monospace' }}
                        stroke="#8b7355"
                        interval="preserveStartEnd"
                      />
                      <YAxis
                        tick={{ fontSize: 12, fill: '#ffd700', fontFamily: 'Courier New, Courier, monospace' }}
                        stroke="#8b7355"
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#2d2418',
                          border: '2px solid #8b7355',
                          borderRadius: '0',
                          color: '#ffd700',
                          fontFamily: 'Courier New, Courier, monospace'
                        }}
                        labelStyle={{ color: '#ffd700', fontFamily: 'Courier New, Courier, monospace' }}
                      />
                      <Legend
                        wrapperStyle={{
                          paddingTop: '5px',
                          paddingBottom: '5px',
                          color: '#ffd700',
                          fontFamily: 'Courier New, Courier, monospace',
                          fontSize: '11px'
                        }}
                        iconSize={12}
                      />
                      <Line
                        type="monotone"
                        dataKey="total"
                        stroke="#ffd700"
                        strokeWidth={2}
                        name="Total"
                        dot={{ fill: '#ffd700', r: 3 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="success"
                        stroke={STATUS_COLORS.success}
                        strokeWidth={2}
                        name="Success"
                        dot={{ fill: STATUS_COLORS.success, r: 3 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="failure"
                        stroke={STATUS_COLORS.failure}
                        strokeWidth={2}
                        name="Failure"
                        dot={{ fill: STATUS_COLORS.failure, r: 3 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="retry"
                        stroke={STATUS_COLORS.retry}
                        strokeWidth={2}
                        name="Retry"
                        dot={{ fill: STATUS_COLORS.retry, r: 3 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              <div>
                <h3 className="osrs-stat-label mb-1">Total Executions</h3>
                <Link
                  to="/task-executions"
                  className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
                  style={{ textDecoration: 'none' }}
                >
                  {executionSummary.total.toLocaleString()}
                </Link>
              </div>
              <div>
                <h3 className="osrs-stat-label mb-1">Success Rate</h3>
                <Link
                  to="/task-executions?status=success"
                  className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
                  style={{
                    color: executionSummary.successRate >= 95 ? '#4caf50' : executionSummary.successRate >= 80 ? '#ff9800' : '#d32f2f',
                    textDecoration: 'none'
                  }}
                >
                  {executionSummary.successRate.toFixed(1)}%
                </Link>
              </div>
              <div>
                <h3 className="osrs-stat-label mb-1">Failure Rate</h3>
                <Link
                  to="/task-executions?status=failure"
                  className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
                  style={{
                    color: executionSummary.failureRate <= 5 ? '#4caf50' : executionSummary.failureRate <= 20 ? '#ff9800' : '#d32f2f',
                    textDecoration: 'none'
                  }}
                >
                  {executionSummary.failureRate.toFixed(1)}%
                </Link>
              </div>
              <div>
                <h3 className="osrs-stat-label mb-1">Avg Duration</h3>
                <p className="osrs-stat-value">
                  {executionSummary.avgDuration > 0
                    ? `${executionSummary.avgDuration.toFixed(2)}s`
                    : '-'}
                </p>
              </div>
              <div>
                <h3 className="osrs-stat-label mb-1">Failures (24h)</h3>
                <Link
                  to="/task-executions?status=failure"
                  className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
                  style={{
                    color: executionSummary.recentFailures24h === 0 ? '#4caf50' : executionSummary.recentFailures24h <= 5 ? '#ff9800' : '#d32f2f',
                    textDecoration: 'none'
                  }}
                >
                  {executionSummary.recentFailures24h}
                </Link>
              </div>
              <div>
                <h3 className="osrs-stat-label mb-1">Failures (7d)</h3>
                <Link
                  to="/task-executions?status=failure"
                  className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
                  style={{
                    color: executionSummary.recentFailures7d === 0 ? '#4caf50' : executionSummary.recentFailures7d <= 20 ? '#ff9800' : '#d32f2f',
                    textDecoration: 'none'
                  }}
                >
                  {executionSummary.recentFailures7d}
                </Link>
              </div>
            </div>

            {/* Status Breakdown */}
            <div>
              <h3 className="osrs-stat-label mb-3">Status Breakdown</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
                {Object.entries(executionSummary.statusBreakdown).map(([status, count]) => {
                  const percentage = executionSummary.total > 0
                    ? ((count / executionSummary.total) * 100).toFixed(1)
                    : '0.0';
                  return (
                    <Link
                      key={status}
                      to={`/task-executions?status=${status}`}
                      className="p-3 rounded hover:opacity-90 transition-opacity cursor-pointer block"
                      style={{
                        backgroundColor: `${STATUS_COLORS[status] || '#fff'}15`,
                        border: `1px solid ${STATUS_COLORS[status] || '#fff'}40`,
                        textDecoration: 'none'
                      }}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span
                          className="text-sm font-semibold capitalize"
                          style={{ color: STATUS_COLORS[status] || '#fff' }}
                        >
                          {status}
                        </span>
                        <span className="text-xs osrs-text-secondary">{percentage}%</span>
                      </div>
                      <p className="text-lg font-bold" style={{ color: STATUS_COLORS[status] || '#fff' }}>
                        {count.toLocaleString()}
                      </p>
                    </Link>
                  );
                })}
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t" style={{ borderColor: '#8b7355' }}>
              <div>
                <h4 className="osrs-stat-label mb-1">Successes</h4>
                <Link
                  to="/task-executions?status=success"
                  className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
                  style={{ color: '#4caf50', textDecoration: 'none' }}
                >
                  {executionSummary.successCount.toLocaleString()}
                </Link>
              </div>
              <div>
                <h4 className="osrs-stat-label mb-1">Failures</h4>
                <Link
                  to="/task-executions?status=failure"
                  className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
                  style={{ color: '#d32f2f', textDecoration: 'none' }}
                >
                  {executionSummary.failureCount.toLocaleString()}
                </Link>
              </div>
              <div>
                <h4 className="osrs-stat-label mb-1">Retries</h4>
                <Link
                  to="/task-executions?status=retry"
                  className="osrs-stat-value hover:opacity-80 transition-opacity cursor-pointer block"
                  style={{ color: '#ff9800', textDecoration: 'none' }}
                >
                  {executionSummary.retryCount.toLocaleString()}
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center py-4">
            <div className="osrs-text-secondary">No execution data available</div>
          </div>
        )}
      </div>

      {/* Quick Actions & Player Management */}
      <div className="osrs-card">
        <h2 className="osrs-card-title mb-6">Quick Actions</h2>
        <div className="space-y-6">
          {/* Add Player Section */}
          <div>
            <h3 className="osrs-stat-label mb-3 flex items-center gap-2">
              <span style={{ color: '#ffd700' }}>➕</span>
              Add New Player
            </h3>
            <form onSubmit={handleAddPlayer} className="flex gap-3">
              <input
                type="text"
                value={newPlayerUsername}
                onChange={(e) => setNewPlayerUsername(e.target.value)}
                placeholder="Enter OSRS username (max 12 chars)"
                className="osrs-btn flex-1"
                style={{
                  backgroundColor: '#3a3024',
                  color: '#ffd700',
                  border: '1px solid #8b7355',
                  padding: '0.75rem 1rem'
                }}
                maxLength={12}
                required
              />
              <button
                type="submit"
                disabled={addingPlayer || !newPlayerUsername.trim()}
                className="osrs-btn"
                style={{
                  minWidth: '140px',
                  opacity: addingPlayer || !newPlayerUsername.trim() ? 0.6 : 1,
                  cursor: addingPlayer || !newPlayerUsername.trim() ? 'not-allowed' : 'pointer'
                }}
              >
                {addingPlayer ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin">⏳</span>
                    Adding...
                  </span>
                ) : (
                  'Add Player'
                )}
              </button>
            </form>
          </div>

          {/* Divider */}
          <div className="border-t" style={{ borderColor: '#8b7355' }}></div>

          {/* Admin Actions */}
          <div>
            <h3 className="osrs-stat-label mb-3 flex items-center gap-2">
              <span style={{ color: '#ffd700' }}>⚙️</span>
              System Actions
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                onClick={handleVerifySchedules}
                disabled={verifyingSchedules}
                className="osrs-btn text-left p-4 hover:opacity-90 transition-opacity"
                style={{
                  backgroundColor: '#3a3024',
                  border: '1px solid #8b7355',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem',
                  minHeight: '80px'
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold osrs-text">Verify Schedules</span>
                  <span style={{ color: '#ffd700', fontSize: '1.2rem' }}>🔍</span>
                </div>
                <span className="text-xs osrs-text-secondary">
                  {verifyingSchedules ? 'Checking schedule integrity...' : 'Validate all player fetch schedules'}
                </span>
              </button>
              <button
                onClick={handleFetchAllPlayers}
                disabled={fetchingAllPlayers}
                className="osrs-btn text-left p-4 hover:opacity-90 transition-opacity"
                style={{
                  backgroundColor: '#3a3024',
                  border: '1px solid #8b7355',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem',
                  minHeight: '80px'
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold osrs-text">Fetch All Players</span>
                  <span style={{ color: '#ffd700', fontSize: '1.2rem' }}>🚀</span>
                </div>
                <span className="text-xs osrs-text-secondary">
                  {fetchingAllPlayers ? 'Triggering fetches...' : 'Manually trigger fetch for all active players'}
                </span>
              </button>
              <button
                onClick={handleGenerateSummaries}
                disabled={generatingSummaries}
                className="osrs-btn text-left p-4 hover:opacity-90 transition-opacity"
                style={{
                  backgroundColor: '#3a3024',
                  border: '1px solid #8b7355',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem',
                  minHeight: '80px'
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold osrs-text">Generate Summaries</span>
                  <span style={{ color: '#ffd700', fontSize: '1.2rem' }}>✨</span>
                </div>
                <span className="text-xs osrs-text-secondary">
                  {generatingSummaries ? 'Generating summaries...' : 'Generate AI summaries for all active players'}
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Players List */}
      <div className="osrs-card">
        <h2 className="osrs-card-title mb-4">Players Management</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full" style={{ borderCollapse: 'separate', borderSpacing: 0 }}>
            <thead>
              <tr style={{ backgroundColor: '#1a1510' }}>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  Username
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  Last Fetched
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  Interval
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {players.map((player) => (
                <tr key={player.id} style={{ borderBottom: '1px solid #8b7355' }} className="hover:opacity-80">
                  <td className="px-6 py-4 whitespace-nowrap font-medium">
                    <button
                      onClick={() => navigate(`/players/${player.username}`)}
                      className="osrs-text hover:opacity-80 font-medium"
                    >
                      {player.username}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className="px-2 inline-flex text-xs leading-5 font-semibold"
                      style={{
                        backgroundColor: player.is_active ? 'rgba(255, 215, 0, 0.2)' : 'rgba(139, 115, 85, 0.2)',
                        border: `1px solid ${player.is_active ? '#ffd700' : '#8b7355'}`,
                        color: player.is_active ? '#ffd700' : '#8b7355'
                      }}
                    >
                      {player.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm osrs-text-secondary">
                    {player.last_fetched
                      ? format(new Date(player.last_fetched), 'MMM d, yyyy HH:mm')
                      : 'Never'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm osrs-text-secondary">
                    {editingInterval === player.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          value={intervalValue}
                          onChange={(e) => setIntervalValue(e.target.value)}
                          min={1}
                          max={10080}
                          className="osrs-btn text-sm"
                          style={{ width: '80px', backgroundColor: '#3a3024', color: '#ffd700' }}
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleSaveInterval(player.username);
                            } else if (e.key === 'Escape') {
                              handleCancelEditInterval();
                            }
                          }}
                        />
                        <button
                          onClick={() => handleSaveInterval(player.username)}
                          className="osrs-text text-xs hover:opacity-80"
                          style={{ color: '#ffd700' }}
                        >
                          Save
                        </button>
                        <button
                          onClick={handleCancelEditInterval}
                          className="osrs-text-secondary text-xs hover:opacity-80"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleStartEditInterval(player.id, player.fetch_interval_minutes)}
                        className="osrs-text hover:opacity-80"
                        title="Click to edit"
                      >
                        {player.fetch_interval_minutes} min
                      </button>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                    <button
                      onClick={() => handleToggleActive(player.username, player.is_active)}
                      className="osrs-text hover:opacity-80"
                    >
                      {player.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button
                      onClick={() => handleTriggerFetch(player.username)}
                      className="osrs-text hover:opacity-80"
                      style={{ color: '#d4af37' }}
                    >
                      Fetch
                    </button>
                    <button
                      onClick={() => handleDeletePlayer(player.username)}
                      className="osrs-text-secondary hover:opacity-80"
                      style={{ color: '#8b7355' }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

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

