import { format } from 'date-fns';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/apiClient';

interface Player {
  id: number;
  username: string;
  created_at: string;
  last_fetched: string | null;
  is_active: boolean;
}

export const Home: React.FC = () => {
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchPlayers();
  }, []);

  const fetchPlayers = async () => {
    try {
      const response = await api.PlayersService.listPlayersApiV1PlayersGet(true);
      setPlayers(response.players);
    } catch (error) {
      console.error('Failed to fetch players:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredPlayers = players.filter((player) =>
    player.username.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return <div className="text-center py-8 osrs-text">Loading players...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="osrs-card-title text-3xl">Player Statistics</h1>
        <input
          type="text"
          placeholder="Search players..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="osrs-btn w-full sm:max-w-xs"
          style={{ backgroundColor: '#3a3024', color: '#ffd700' }}
        />
      </div>

      {filteredPlayers.length === 0 ? (
        <div className="osrs-card text-center py-12">
          <p className="osrs-text-secondary">No players found. Use the search to find a player.</p>
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
                    Last Fetched
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
                        ? format(new Date(player.last_fetched), 'MMM d, yyyy HH:mm')
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
        </div>
      )}
    </div>
  );
};

