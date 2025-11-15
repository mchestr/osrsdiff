import { useEffect, useState } from 'react';
import { api } from '../api/apiClient';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Modal } from '../components/Modal';
import type { PlayerResponse } from '../api/models/PlayerResponse';
import {
  NewPlayersChart,
  PlayerTable,
} from '../components/admin';
import { useModal } from '../hooks';
import { useNotificationContext } from '../contexts/NotificationContext';
import { extractErrorMessage } from '../utils/errorHandler';

export const AdminPlayerList: React.FC = () => {
  const [players, setPlayers] = useState<PlayerResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showInactive, setShowInactive] = useState(true);
  const [editingInterval, setEditingInterval] = useState<number | null>(null);
  const [intervalValue, setIntervalValue] = useState<string>('');
  const [deletingPlayer, setDeletingPlayer] = useState<string | null>(null);
  const [activatingPlayer, setActivatingPlayer] = useState<string | null>(null);
  const [recalculatingGameMode, setRecalculatingGameMode] = useState<string | null>(null);

  // Modal state (for confirmations only)
  const { modalState, showConfirmModal, closeModal, handleConfirm } = useModal();
  const { showNotification } = useNotificationContext();

  useEffect(() => {
    fetchPlayers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showInactive]);

  const fetchPlayers = async () => {
    try {
      setLoading(true);
      const response = await api.PlayersService.listPlayersApiV1PlayersGet(!showInactive);
      setPlayers(response.players);
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to fetch players');
      showNotification(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePlayer = async (username: string) => {
    setDeletingPlayer(username);
    try {
      await api.PlayersService.removePlayerApiV1PlayersUsernameDelete(username);
      await fetchPlayers();
      showNotification(`Player '${username}' deleted successfully`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to delete player');
      showNotification(errorMessage, 'error');
    } finally {
      setDeletingPlayer(null);
    }
  };

  const handleDeactivatePlayer = async (username: string) => {
    setActivatingPlayer(username);
    try {
      await api.PlayersService.deactivatePlayerApiV1PlayersUsernameDeactivatePost(username);
      await fetchPlayers();
      showNotification(`Player '${username}' deactivated successfully`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to deactivate player');
      showNotification(errorMessage, 'error');
    } finally {
      setActivatingPlayer(null);
    }
  };

  const handleReactivatePlayer = async (username: string) => {
    setActivatingPlayer(username);
    try {
      await api.PlayersService.reactivatePlayerApiV1PlayersUsernameReactivatePost(username);
      await fetchPlayers();
      showNotification(`Player '${username}' reactivated successfully`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to reactivate player');
      showNotification(errorMessage, 'error');
    } finally {
      setActivatingPlayer(null);
    }
  };

  const handleUpdateInterval = async (username: string, interval: number) => {
    try {
      await api.PlayersService.updatePlayerFetchIntervalApiV1PlayersUsernameFetchIntervalPut(
        username,
        { fetch_interval_minutes: interval }
      );
      await fetchPlayers();
      setEditingInterval(null);
      setIntervalValue('');
      showNotification(`Fetch interval updated for '${username}'`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to update interval');
      showNotification(errorMessage, 'error');
    }
  };

  const handleTriggerFetch = async (username: string) => {
    try {
      await api.PlayersService.triggerManualFetchApiV1PlayersUsernameFetchPost(username);
      showNotification(`Manual fetch triggered for '${username}'`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to trigger fetch');
      showNotification(errorMessage, 'error');
    }
  };

  const handleRecalculateGameMode = async (username: string) => {
    setRecalculatingGameMode(username);
    try {
      const updatedPlayer = await api.PlayersService.recalculateGameModeApiV1PlayersUsernameRecalculateGameModePost(username);
      await fetchPlayers();
      const gameModeDisplay = updatedPlayer.game_mode ? updatedPlayer.game_mode.charAt(0).toUpperCase() + updatedPlayer.game_mode.slice(1) : 'Unknown';
      showNotification(`Game mode recalculated for '${username}': ${gameModeDisplay}`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to recalculate game mode');
      showNotification(errorMessage, 'error');
    } finally {
      setRecalculatingGameMode(null);
    }
  };

  const confirmDelete = (username: string) => {
    showConfirmModal(
      'Confirm Delete',
      `Are you sure you want to delete player '${username}'? This will remove all their historical data and cannot be undone.`,
      () => handleDeletePlayer(username),
      'warning'
    );
  };

  // Note: Filtering is now handled by DataTable's built-in search
  const filteredPlayers = players;

  const handleStartEditInterval = (playerId: number, currentInterval: number) => {
    setEditingInterval(playerId);
    setIntervalValue(currentInterval.toString());
  };

  const handleSaveInterval = async (username: string, interval: number) => {
    await handleUpdateInterval(username, interval);
  };

  const handleCancelEditInterval = () => {
    setEditingInterval(null);
    setIntervalValue('');
  };

  if (loading) {
    return <LoadingSpinner message="Loading players..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-4">
        <h1 className="osrs-card-title text-2xl sm:text-3xl">Player Management</h1>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 osrs-text text-sm sm:text-base cursor-pointer">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="w-5 h-5 sm:w-4 sm:h-4 cursor-pointer"
              style={{ accentColor: '#ffd700' }}
            />
            Show Inactive
          </label>
        </div>
      </div>

      {/* New Players Chart */}
      <NewPlayersChart players={players} />

      {/* Players Table */}
      <PlayerTable
        players={filteredPlayers}
        editingInterval={editingInterval}
        intervalValue={intervalValue}
        onIntervalValueChange={setIntervalValue}
        onStartEditInterval={handleStartEditInterval}
        onSaveInterval={handleSaveInterval}
        onCancelEditInterval={handleCancelEditInterval}
        onTriggerFetch={handleTriggerFetch}
        onRecalculateGameMode={handleRecalculateGameMode}
        onDeactivate={handleDeactivatePlayer}
        onReactivate={handleReactivatePlayer}
        onDelete={confirmDelete}
        activatingPlayer={activatingPlayer}
        deletingPlayer={deletingPlayer}
        recalculatingGameMode={recalculatingGameMode}
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

