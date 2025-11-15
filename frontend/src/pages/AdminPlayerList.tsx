import { useEffect, useState } from 'react';
import { api } from '../api/apiClient';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Modal } from '../components/Modal';
import type { PlayerResponse } from '../api/models/PlayerResponse';
import {
  AddPlayerForm,
  PlayerSearchBar,
  PlayerTable,
} from '../components/admin';
import { useModal } from '../hooks';
import { extractErrorMessage } from '../utils/errorHandler';

export const AdminPlayerList: React.FC = () => {
  const [players, setPlayers] = useState<PlayerResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showInactive, setShowInactive] = useState(true);
  const [newPlayerUsername, setNewPlayerUsername] = useState('');
  const [addingPlayer, setAddingPlayer] = useState(false);
  const [editingInterval, setEditingInterval] = useState<number | null>(null);
  const [intervalValue, setIntervalValue] = useState<string>('');
  const [deletingPlayer, setDeletingPlayer] = useState<string | null>(null);
  const [activatingPlayer, setActivatingPlayer] = useState<string | null>(null);

  // Modal state
  const { modalState, showModal, showConfirmModal, closeModal, handleConfirm } = useModal();

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
      showModal('Error', errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleAddPlayer = async () => {
    if (!newPlayerUsername.trim()) {
      showModal('Error', 'Please enter a username', 'error');
      return;
    }

    const username = newPlayerUsername.trim();
    setAddingPlayer(true);
    try {
      await api.PlayersService.addPlayerApiV1PlayersPost({
        username,
      });
      setNewPlayerUsername('');
      await fetchPlayers();
      showModal('Success', `Player '${username}' added successfully`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to add player');
      showModal('Error', errorMessage, 'error');
    } finally {
      setAddingPlayer(false);
    }
  };

  const handleDeletePlayer = async (username: string) => {
    setDeletingPlayer(username);
    try {
      await api.PlayersService.removePlayerApiV1PlayersUsernameDelete(username);
      await fetchPlayers();
      showModal('Success', `Player '${username}' deleted successfully`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to delete player');
      showModal('Error', errorMessage, 'error');
    } finally {
      setDeletingPlayer(null);
    }
  };

  const handleDeactivatePlayer = async (username: string) => {
    setActivatingPlayer(username);
    try {
      await api.PlayersService.deactivatePlayerApiV1PlayersUsernameDeactivatePost(username);
      await fetchPlayers();
      showModal('Success', `Player '${username}' deactivated successfully`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to deactivate player');
      showModal('Error', errorMessage, 'error');
    } finally {
      setActivatingPlayer(null);
    }
  };

  const handleReactivatePlayer = async (username: string) => {
    setActivatingPlayer(username);
    try {
      await api.PlayersService.reactivatePlayerApiV1PlayersUsernameReactivatePost(username);
      await fetchPlayers();
      showModal('Success', `Player '${username}' reactivated successfully`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to reactivate player');
      showModal('Error', errorMessage, 'error');
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
      showModal('Success', `Fetch interval updated for '${username}'`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to update interval');
      showModal('Error', errorMessage, 'error');
    }
  };

  const handleTriggerFetch = async (username: string) => {
    try {
      await api.PlayersService.triggerManualFetchApiV1PlayersUsernameFetchPost(username);
      showModal('Success', `Manual fetch triggered for '${username}'`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to trigger fetch');
      showModal('Error', errorMessage, 'error');
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

  const filteredPlayers = players.filter((player) =>
    player.username.toLowerCase().includes(searchTerm.toLowerCase())
  );

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

      {/* Add Player Section */}
      <AddPlayerForm
        username={newPlayerUsername}
        onUsernameChange={setNewPlayerUsername}
        onAdd={handleAddPlayer}
        adding={addingPlayer}
      />

      {/* Search */}
      <PlayerSearchBar
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
      />

      {/* Players Table */}
      {filteredPlayers.length === 0 ? (
        <div className="osrs-card text-center py-12">
          <p className="osrs-text-secondary">
            {searchTerm ? 'No players match your search.' : 'No players found.'}
          </p>
        </div>
      ) : (
        <PlayerTable
          players={filteredPlayers}
          editingInterval={editingInterval}
          intervalValue={intervalValue}
          onIntervalValueChange={setIntervalValue}
          onStartEditInterval={handleStartEditInterval}
          onSaveInterval={handleSaveInterval}
          onCancelEditInterval={handleCancelEditInterval}
          onTriggerFetch={handleTriggerFetch}
          onDeactivate={handleDeactivatePlayer}
          onReactivate={handleReactivatePlayer}
          onDelete={confirmDelete}
          activatingPlayer={activatingPlayer}
          deletingPlayer={deletingPlayer}
        />
      )}

      {/* Modal */}
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

