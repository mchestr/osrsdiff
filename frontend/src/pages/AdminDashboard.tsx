import { format } from 'date-fns';
import { useEffect, useState } from 'react';
import apiClient from '../lib/api';

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
  uptime_info: Record<string, any>;
}

export const AdminDashboard: React.FC = () => {
  const [players, setPlayers] = useState<Player[]>([]);
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [newPlayerUsername, setNewPlayerUsername] = useState('');
  const [addingPlayer, setAddingPlayer] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [playersRes, statsRes, healthRes] = await Promise.all([
        apiClient.get('/api/v1/players?active_only=false'),
        apiClient.get('/api/v1/system/stats'),
        apiClient.get('/api/v1/system/health'),
      ]);

      setPlayers(playersRes.data.players);
      setStats(statsRes.data);
      setHealth(healthRes.data);
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
      await apiClient.post('/api/v1/players', {
        username: newPlayerUsername.trim(),
      });
      setNewPlayerUsername('');
      await fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to add player');
    } finally {
      setAddingPlayer(false);
    }
  };

  const handleToggleActive = async (username: string, isActive: boolean) => {
    try {
      if (isActive) {
        await apiClient.post(`/api/v1/players/${username}/deactivate`);
      } else {
        await apiClient.post(`/api/v1/players/${username}/reactivate`);
      }
      await fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update player');
    }
  };

  const handleDeletePlayer = async (username: string) => {
    if (!confirm(`Are you sure you want to delete player "${username}"?`)) {
      return;
    }

    try {
      await apiClient.delete(`/api/v1/players/${username}`);
      await fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to delete player');
    }
  };

  const handleTriggerFetch = async (username: string) => {
    try {
      await apiClient.post(`/api/v1/players/${username}/fetch`);
      alert('Fetch task enqueued successfully');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to trigger fetch');
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>

      {/* System Health */}
      {health && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card">
            <h3 className="text-sm font-medium text-gray-500 mb-2">System Status</h3>
            <p
              className={`text-2xl font-bold ${
                health.status === 'healthy' ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {health.status.toUpperCase()}
            </p>
          </div>
          <div className="card">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Database</h3>
            <p
              className={`text-2xl font-bold ${
                health.database_connected ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {health.database_connected ? 'Connected' : 'Disconnected'}
            </p>
          </div>
          {health.total_storage_mb && (
            <div className="card">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Storage</h3>
              <p className="text-2xl font-bold text-primary-600">
                {health.total_storage_mb.toFixed(2)} MB
              </p>
            </div>
          )}
        </div>
      )}

      {/* Database Stats */}
      {stats && (
        <div className="card">
          <h2 className="text-xl font-bold mb-4">Database Statistics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">Total Players</h3>
              <p className="text-2xl font-bold">{stats.total_players}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">Active Players</h3>
              <p className="text-2xl font-bold text-green-600">{stats.active_players}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">Total Records</h3>
              <p className="text-2xl font-bold">{stats.total_hiscore_records.toLocaleString()}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">Records (24h)</h3>
              <p className="text-2xl font-bold">{stats.records_last_24h}</p>
            </div>
          </div>
        </div>
      )}

      {/* Add Player */}
      <div className="card">
        <h2 className="text-xl font-bold mb-4">Add New Player</h2>
        <form onSubmit={handleAddPlayer} className="flex gap-4">
          <input
            type="text"
            value={newPlayerUsername}
            onChange={(e) => setNewPlayerUsername(e.target.value)}
            placeholder="Enter OSRS username"
            className="input flex-1"
            maxLength={12}
            required
          />
          <button
            type="submit"
            disabled={addingPlayer}
            className="btn btn-primary"
          >
            {addingPlayer ? 'Adding...' : 'Add Player'}
          </button>
        </form>
      </div>

      {/* Players List */}
      <div className="card">
        <h2 className="text-xl font-bold mb-4">Players Management</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Username
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Last Fetched
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Interval
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {players.map((player) => (
                <tr key={player.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap font-medium">
                    {player.username}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        player.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {player.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {player.last_fetched
                      ? format(new Date(player.last_fetched), 'MMM d, yyyy HH:mm')
                      : 'Never'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {player.fetch_interval_minutes} min
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                    <button
                      onClick={() => handleToggleActive(player.username, player.is_active)}
                      className="text-primary-600 hover:text-primary-900"
                    >
                      {player.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button
                      onClick={() => handleTriggerFetch(player.username)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      Fetch
                    </button>
                    <button
                      onClick={() => handleDeletePlayer(player.username)}
                      className="text-red-600 hover:text-red-900"
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
    </div>
  );
};

