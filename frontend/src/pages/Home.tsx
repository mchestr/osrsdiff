import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/apiClient';
import { useAuth } from '../contexts/AuthContext';

interface Player {
  id: number;
  username: string;
  created_at: string;
  last_fetched: string | null;
  is_active: boolean;
}

export const Home: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      fetchPlayers();
    }
  }, [isAuthenticated]);

  const fetchPlayers = async () => {
    try {
      setLoading(true);
      const response = await api.PlayersService.listPlayersApiV1PlayersGet(true);
      setPlayers(response.players);
    } catch (error) {
      console.error('Failed to fetch players:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/players/${encodeURIComponent(searchTerm.trim())}`);
    }
  };

  const filteredPlayers = players.filter((player) =>
    player.username.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="osrs-card text-center py-12">
        <h1 className="osrs-card-title text-4xl md:text-5xl mb-4">
          OSRS Diff
        </h1>
        <p className="osrs-text text-lg md:text-xl mb-6 max-w-2xl mx-auto">
          Track and analyze Old School RuneScape player statistics over time.
          View detailed skill progress, boss kill counts, and historical data for any tracked player.
        </p>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="max-w-2xl mx-auto">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Search for a player by username..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1 osrs-btn"
              style={{ backgroundColor: '#3a3024', color: '#ffd700', fontSize: '1rem', padding: '0.75rem 1rem' }}
            />
            <button
              type="submit"
              className="osrs-btn px-6"
              style={{ whiteSpace: 'nowrap' }}
            >
              Search
            </button>
          </div>
        </form>
      </div>

      {/* Features Section */}
      <div className="grid md:grid-cols-3 gap-6">
        <div className="osrs-card">
          <h3 className="osrs-card-title text-xl mb-2">📊 Skill Tracking</h3>
          <p className="osrs-text-secondary">
            Monitor skill levels and experience gains over time with detailed progress charts and statistics.
          </p>
        </div>
        <div className="osrs-card">
          <h3 className="osrs-card-title text-xl mb-2">⚔️ Boss Progress</h3>
          <p className="osrs-text-secondary">
            Track boss kill counts and analyze your PvM progress with historical data and trends.
          </p>
        </div>
        <div className="osrs-card">
          <h3 className="osrs-card-title text-xl mb-2">📈 Analytics</h3>
          <p className="osrs-text-secondary">
            Get insights into your gameplay with daily rates, progress summaries, and time estimates.
          </p>
        </div>
      </div>

      {/* Tracked Players Section - Only shown when authenticated */}
      {isAuthenticated && (
        <div className="osrs-card">
          <h2 className="osrs-card-title text-2xl mb-4">Tracked Players</h2>
          {loading ? (
            <div className="text-center py-8 osrs-text">Loading players...</div>
          ) : filteredPlayers.length === 0 ? (
            <div className="text-center py-8">
              <p className="osrs-text-secondary mb-4">
                {searchTerm ? 'No players found matching your search.' : 'No players are currently being tracked.'}
              </p>
              {searchTerm && (
                <button
                  onClick={() => navigate(`/players/${encodeURIComponent(searchTerm.trim())}`)}
                  className="osrs-btn"
                >
                  View {searchTerm} anyway
                </button>
              )}
            </div>
          ) : (
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
                      Last Updated
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
                      className="hover:opacity-80 cursor-pointer"
                      onClick={() => navigate(`/players/${player.username}`)}
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
                        {player.last_fetched
                          ? new Date(player.last_fetched).toLocaleDateString()
                          : 'Never'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/players/${player.username}`);
                          }}
                          className="osrs-btn text-sm"
                        >
                          View Stats
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
