import { useEffect, useState } from 'react';
import { api } from '../api/apiClient';
import { Modal } from '../components/Modal';
import type { PlayerResponse } from '../api/models/PlayerResponse';
import {
  AddPlayerForm,
  PlayerSearchBar,
  PlayerTable,
} from '../components/admin';

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
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalMessage, setModalMessage] = useState<string | React.ReactNode>('');
  const [modalType, setModalType] = useState<'info' | 'error' | 'success' | 'warning'>('info');
  const [modalShowConfirm, setModalShowConfirm] = useState(false);
  const [modalConfirmCallback, setModalConfirmCallback] = useState<(() => void) | null>(null);

  useEffect(() => {
    fetchPlayers();
  }, [showInactive]);

  const fetchPlayers = async () => {
    try {
      setLoading(true);
      const response = await api.PlayersService.listPlayersApiV1PlayersGet(!showInactive);
      setPlayers(response.players);
    } catch (error) {
      console.error('Failed to fetch players:', error);
      showModal('Error', 'Failed to fetch players', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showModal = (
    title: string,
    message: string | React.ReactNode,
    type: 'info' | 'error' | 'success' | 'warning' = 'info',
    showConfirm = false,
    onConfirm: (() => void) | null = null
  ) => {
    setModalTitle(title);
    setModalMessage(message);
    setModalType(type);
    setModalShowConfirm(showConfirm);
    setModalConfirmCallback(onConfirm ? () => onConfirm() : null);
    setModalOpen(true);
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
      const errorMessage = error instanceof Error ? error.message : 'Failed to add player';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
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
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete player';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
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
      const errorMessage = error instanceof Error ? error.message : 'Failed to deactivate player';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
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
      const errorMessage = error instanceof Error ? error.message : 'Failed to reactivate player';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
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
      const errorMessage = error instanceof Error ? error.message : 'Failed to update interval';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
    }
  };

  const handleTriggerFetch = async (username: string) => {
    try {
      await api.PlayersService.triggerManualFetchApiV1PlayersUsernameFetchPost(username);
      showModal('Success', `Manual fetch triggered for '${username}'`, 'success');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to trigger fetch';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      showModal('Error', errorDetail || errorMessage, 'error');
    }
  };

  const confirmDelete = (username: string) => {
    showModal(
      'Confirm Delete',
      `Are you sure you want to delete player '${username}'? This will remove all their historical data and cannot be undone.`,
      'warning',
      true,
      () => handleDeletePlayer(username)
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
    return <div className="text-center py-8 osrs-text">Loading players...</div>;
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
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setModalShowConfirm(false);
          setModalConfirmCallback(null);
        }}
        title={modalTitle}
        type={modalType}
        showConfirm={modalShowConfirm}
        onConfirm={() => {
          if (modalConfirmCallback) {
            modalConfirmCallback();
          }
          setModalOpen(false);
          setModalShowConfirm(false);
          setModalConfirmCallback(null);
        }}
      >
        {modalMessage}
      </Modal>
    </div>
  );
};

