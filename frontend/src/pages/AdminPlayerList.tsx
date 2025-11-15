import { format } from 'date-fns';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/apiClient';
import { Modal } from '../components/Modal';
import type { PlayerResponse } from '../api/models/PlayerResponse';

export const AdminPlayerList: React.FC = () => {
  const navigate = useNavigate();
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

    setAddingPlayer(true);
    try {
      await api.PlayersService.addPlayerApiV1PlayersPost({
        username: newPlayerUsername.trim(),
      });
      setNewPlayerUsername('');
      await fetchPlayers();
      showModal('Success', `Player '${newPlayerUsername.trim()}' added successfully`, 'success');
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

  if (loading) {
    return <div className="text-center py-8 osrs-text">Loading players...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="osrs-card-title text-3xl">Player Management</h1>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 osrs-text">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="osrs-btn"
            />
            Show Inactive
          </label>
        </div>
      </div>

      {/* Add Player Section */}
      <div className="osrs-card">
        <h2 className="osrs-card-title text-xl mb-4">Add New Player</h2>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Enter username..."
            value={newPlayerUsername}
            onChange={(e) => setNewPlayerUsername(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleAddPlayer();
              }
            }}
            className="flex-1 osrs-btn"
            maxLength={12}
          />
          <button
            onClick={handleAddPlayer}
            disabled={addingPlayer || !newPlayerUsername.trim()}
            className="osrs-btn px-6"
          >
            {addingPlayer ? 'Adding...' : 'Add Player'}
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="flex gap-4">
        <input
          type="text"
          placeholder="Search players..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="flex-1 osrs-btn"
        />
      </div>

      {/* Players Table */}
      {filteredPlayers.length === 0 ? (
        <div className="osrs-card text-center py-12">
          <p className="osrs-text-secondary">
            {searchTerm ? 'No players match your search.' : 'No players found.'}
          </p>
        </div>
      ) : (
        <div className="osrs-card">
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
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                    Last Fetched
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                    Fetch Interval
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase" style={{ borderBottom: '2px solid #8b7355' }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredPlayers.map((player) => (
                  <tr
                    key={player.id}
                    style={{ borderBottom: '1px solid #8b7355' }}
                    className="hover:opacity-80"
                  >
                    <td className="px-6 py-4 whitespace-nowrap font-medium">
                      <span className="osrs-text">{player.username}</span>
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
                      {format(new Date(player.created_at), 'MMM d, yyyy')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm osrs-text-secondary">
                      {player.last_fetched
                        ? format(new Date(player.last_fetched), 'MMM d, HH:mm')
                        : 'Never'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {editingInterval === player.id ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            value={intervalValue}
                            onChange={(e) => setIntervalValue(e.target.value)}
                            className="osrs-btn w-20 text-sm"
                            min="1"
                            max="10080"
                            autoFocus
                            onKeyPress={(e) => {
                              if (e.key === 'Enter') {
                                const interval = parseInt(intervalValue);
                                if (interval >= 1 && interval <= 10080) {
                                  handleUpdateInterval(player.username, interval);
                                }
                              } else if (e.key === 'Escape') {
                                setEditingInterval(null);
                                setIntervalValue('');
                              }
                            }}
                          />
                          <button
                            onClick={() => {
                              const interval = parseInt(intervalValue);
                              if (interval >= 1 && interval <= 10080) {
                                handleUpdateInterval(player.username, interval);
                              }
                            }}
                            className="osrs-btn text-xs px-2 py-1"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => {
                              setEditingInterval(null);
                              setIntervalValue('');
                            }}
                            className="osrs-btn text-xs px-2 py-1"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <span
                          className="text-sm osrs-text-secondary cursor-pointer hover:text-[#ffd700]"
                          onClick={() => {
                            setEditingInterval(player.id);
                            setIntervalValue(player.fetch_interval_minutes.toString());
                          }}
                          title="Click to edit"
                        >
                          {player.fetch_interval_minutes} min
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2 flex-wrap">
                        <button
                          onClick={() => navigate(`/players/${player.username}`)}
                          className="osrs-btn text-xs px-2 py-1"
                        >
                          View
                        </button>
                        <button
                          onClick={() => handleTriggerFetch(player.username)}
                          className="osrs-btn text-xs px-2 py-1"
                          title="Trigger manual fetch"
                        >
                          Fetch
                        </button>
                        {player.is_active ? (
                          <button
                            onClick={() => handleDeactivatePlayer(player.username)}
                            disabled={activatingPlayer === player.username}
                            className="osrs-btn text-xs px-2 py-1"
                            style={{
                              backgroundColor: '#3a3024',
                              opacity: activatingPlayer === player.username ? 0.5 : 1
                            }}
                          >
                            {activatingPlayer === player.username ? '...' : 'Deactivate'}
                          </button>
                        ) : (
                          <button
                            onClick={() => handleReactivatePlayer(player.username)}
                            disabled={activatingPlayer === player.username}
                            className="osrs-btn text-xs px-2 py-1"
                            style={{
                              backgroundColor: '#3a3024',
                              opacity: activatingPlayer === player.username ? 0.5 : 1
                            }}
                          >
                            {activatingPlayer === player.username ? '...' : 'Activate'}
                          </button>
                        )}
                        <button
                          onClick={() => confirmDelete(player.username)}
                          disabled={deletingPlayer === player.username}
                          className="osrs-btn text-xs px-2 py-1"
                          style={{
                            backgroundColor: '#4a3024',
                            borderColor: '#ff6b6b',
                            color: '#ff6b6b',
                            opacity: deletingPlayer === player.username ? 0.5 : 1
                          }}
                        >
                          {deletingPlayer === player.username ? '...' : 'Delete'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 text-sm osrs-text-secondary text-center">
            Showing {filteredPlayers.length} of {players.length} players
          </div>
        </div>
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
        message={modalMessage}
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
      />
    </div>
  );
};

