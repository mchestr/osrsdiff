import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/apiClient';

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
    return <div className="text-center py-8">Loading players...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Player Statistics</h1>
        <input
          type="text"
          placeholder="Search players..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input max-w-xs"
        />
      </div>

      {filteredPlayers.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500">No players found. Use the search to find a player.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredPlayers.map((player) => (
            <div
              key={player.id}
              className="card cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => navigate(`/players/${player.username}`)}
            >
              <h3 className="text-xl font-bold text-primary-600 mb-2">
                {player.username}
              </h3>
              <div className="space-y-1 text-sm text-gray-600">
                <p>
                  Status:{' '}
                  <span
                    className={`font-semibold ${
                      player.is_active ? 'text-green-600' : 'text-gray-500'
                    }`}
                  >
                    {player.is_active ? 'Active' : 'Inactive'}
                  </span>
                </p>
                {player.last_fetched && (
                  <p>
                    Last updated:{' '}
                    {new Date(player.last_fetched).toLocaleDateString()}
                  </p>
                )}
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/players/${player.username}`);
                }}
                className="mt-4 btn btn-primary w-full"
              >
                View Stats
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

