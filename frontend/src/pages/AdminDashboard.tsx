import { format } from 'date-fns';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/apiClient';
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

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalMessage, setModalMessage] = useState<string | React.ReactNode>('');
  const [modalType, setModalType] = useState<'info' | 'error' | 'success' | 'warning'>('info');
  const [modalShowConfirm, setModalShowConfirm] = useState(false);
  const [modalConfirmCallback, setModalConfirmCallback] = useState<(() => void) | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

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

  if (loading) {
    return <div className="text-center py-8 osrs-text">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="osrs-card-title text-3xl">Admin Dashboard</h1>

      {/* System Health */}
      {health && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="osrs-card">
            <h3 className="osrs-stat-label mb-2">System Status</h3>
            <p
              className="osrs-stat-value"
              style={{ color: health.status === 'healthy' ? '#ffd700' : '#d4af37' }}
            >
              {health.status.toUpperCase()}
            </p>
          </div>
          <div className="osrs-card">
            <h3 className="osrs-stat-label mb-2">Database</h3>
            <p
              className="osrs-stat-value"
              style={{ color: health.database_connected ? '#ffd700' : '#d4af37' }}
            >
              {health.database_connected ? 'Connected' : 'Disconnected'}
            </p>
          </div>
          {health.total_storage_mb && (
            <div className="osrs-card">
              <h3 className="osrs-stat-label mb-2">Storage</h3>
              <p className="osrs-stat-value">
                {health.total_storage_mb.toFixed(2)} MB
              </p>
            </div>
          )}
        </div>
      )}

      {/* Database Stats */}
      {stats && (
        <div className="osrs-card">
          <h2 className="osrs-card-title mb-4">Database Statistics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <h3 className="osrs-stat-label mb-1">Total Players</h3>
              <p className="osrs-stat-value">{stats.total_players}</p>
            </div>
            <div>
              <h3 className="osrs-stat-label mb-1">Active Players</h3>
              <p className="osrs-stat-value" style={{ color: '#ffd700' }}>{stats.active_players}</p>
            </div>
            <div>
              <h3 className="osrs-stat-label mb-1">Total Records</h3>
              <p className="osrs-stat-value">{stats.total_hiscore_records.toLocaleString()}</p>
            </div>
            <div>
              <h3 className="osrs-stat-label mb-1">Records (24h)</h3>
              <p className="osrs-stat-value">{stats.records_last_24h}</p>
            </div>
          </div>
        </div>
      )}

      {/* Admin Actions */}
      <div className="osrs-card">
        <h2 className="osrs-card-title mb-4">Admin Actions</h2>
        <div className="flex gap-4 flex-wrap">
          <button
            onClick={handleVerifySchedules}
            disabled={verifyingSchedules}
            className="osrs-btn"
            style={{ minWidth: '200px' }}
          >
            {verifyingSchedules ? 'Verifying...' : 'Verify Schedules'}
          </button>
          <button
            onClick={handleFetchAllPlayers}
            disabled={fetchingAllPlayers}
            className="osrs-btn"
            style={{ minWidth: '200px' }}
          >
            {fetchingAllPlayers ? 'Triggering...' : 'Fetch All Active Players'}
          </button>
        </div>
      </div>

      {/* Add Player */}
      <div className="osrs-card">
        <h2 className="osrs-card-title mb-4">Add New Player</h2>
        <form onSubmit={handleAddPlayer} className="flex gap-4">
          <input
            type="text"
            value={newPlayerUsername}
            onChange={(e) => setNewPlayerUsername(e.target.value)}
            placeholder="Enter OSRS username"
            className="osrs-btn flex-1"
            style={{ backgroundColor: '#3a3024', color: '#ffd700' }}
            maxLength={12}
            required
          />
          <button
            type="submit"
            disabled={addingPlayer}
            className="osrs-btn"
          >
            {addingPlayer ? 'Adding...' : 'Add Player'}
          </button>
        </form>
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

