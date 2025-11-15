import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/apiClient';
import type { DatabaseStatsResponse } from '../api/models/DatabaseStatsResponse';

export const Home: React.FC = () => {
  const [stats, setStats] = useState<DatabaseStatsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.SystemService.getDatabaseStatsApiV1SystemStatsGet();
      setStats(response);
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/players/${encodeURIComponent(searchTerm.trim())}`);
    }
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(2) + 'm';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'k';
    }
    return num.toLocaleString();
  };

  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <div className="text-center py-8 sm:py-12 md:py-16 px-2">
        <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold mb-4 sm:mb-6" style={{ color: '#ffd700' }}>
          OSRS Diff
        </h1>
        <p className="osrs-text text-lg sm:text-xl md:text-2xl mb-6 sm:mb-8 max-w-3xl mx-auto px-2">
          The open source Old School RuneScape<br className="hidden sm:block" />
          <span className="sm:hidden"> </span>player progress tracker.
        </p>

        {/* Statistics Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 max-w-4xl mx-auto mt-8 sm:mt-12 px-2">
            {loading ? (
              <>
                <div className="text-center">
                  <div className="text-4xl md:text-5xl font-bold mb-2" style={{ color: '#ffd700' }}>...</div>
                  <div className="osrs-text-secondary text-sm md:text-base">Players</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl md:text-5xl font-bold mb-2" style={{ color: '#ffd700' }}>...</div>
                  <div className="osrs-text-secondary text-sm md:text-base">Snapshots</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl md:text-5xl font-bold mb-2" style={{ color: '#ffd700' }}>...</div>
                  <div className="osrs-text-secondary text-sm md:text-base">Active</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl md:text-5xl font-bold mb-2" style={{ color: '#ffd700' }}>...</div>
                  <div className="osrs-text-secondary text-sm md:text-base">Last 24h</div>
                </div>
              </>
            ) : stats ? (
              <>
                <div className="text-center">
                  <div className="text-4xl md:text-5xl font-bold mb-2" style={{ color: '#ffd700' }}>
                    {formatNumber(stats.total_players)}
                  </div>
                  <div className="osrs-text-secondary text-sm md:text-base">Players</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl md:text-5xl font-bold mb-2" style={{ color: '#ffd700' }}>
                    {formatNumber(stats.total_hiscore_records)}
                  </div>
                  <div className="osrs-text-secondary text-sm md:text-base">Snapshots</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl md:text-5xl font-bold mb-2" style={{ color: '#ffd700' }}>
                    {formatNumber(stats.active_players)}
                  </div>
                  <div className="osrs-text-secondary text-sm md:text-base">Active</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl md:text-5xl font-bold mb-2" style={{ color: '#ffd700' }}>
                    {formatNumber(stats.records_last_24h)}
                  </div>
                  <div className="osrs-text-secondary text-sm md:text-base">Last 24h</div>
                </div>
              </>
            ) : null}
          </div>

        {/* Search Form */}
        <div className="max-w-2xl mx-auto mt-8 sm:mt-12 px-2">
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2 sm:gap-2">
            <input
              type="text"
              placeholder="Search for a player by username..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1 osrs-btn text-base sm:text-lg py-2.5 sm:py-3"
            />
            <button
              type="submit"
              className="osrs-btn px-6 sm:px-8 text-base sm:text-lg py-2.5 sm:py-3 w-full sm:w-auto"
            >
              Search
            </button>
          </form>
        </div>
      </div>

      {/* Track your hiscores over time */}
      <div className="osrs-card">
        <h2 className="osrs-card-title text-xl sm:text-2xl md:text-3xl mb-4 sm:mb-6 text-center">Track your hiscores over time</h2>
        <p className="osrs-text text-base sm:text-lg mb-6 sm:mb-8 text-center max-w-2xl mx-auto px-2">
          By periodically checking your hiscores, OSRS Diff can create a historical record, this allows you to:
        </p>
        <div className="grid md:grid-cols-3 gap-4 sm:gap-6">
          <div className="text-center">
            <div className="text-4xl mb-4">📊</div>
            <h3 className="osrs-card-title text-xl mb-2">Check your gains, all-time records and collect achievements</h3>
            <p className="osrs-text-secondary">
              Monitor skill levels and experience gains over time with detailed progress charts and statistics.
            </p>
          </div>
          <div className="text-center">
            <div className="text-4xl mb-4">📈</div>
            <h3 className="osrs-card-title text-xl mb-2">Visualise your in-game activity</h3>
            <p className="osrs-text-secondary">
              Get insights into your gameplay with daily rates, progress summaries, and time estimates.
            </p>
          </div>
          <div className="text-center">
            <div className="text-4xl mb-4">⚔️</div>
            <h3 className="osrs-card-title text-xl mb-2">Track boss progress</h3>
            <p className="osrs-text-secondary">
              Track boss kill counts and analyze your PvM progress with historical data and trends.
            </p>
          </div>
        </div>
      </div>

      {/* How does it work? */}
      <div className="osrs-card">
        <h2 className="osrs-card-title text-xl sm:text-2xl md:text-3xl mb-6 sm:mb-8 text-center">How does it work?</h2>
        <div className="grid md:grid-cols-3 gap-6 sm:gap-8 max-w-4xl mx-auto px-2">
          <div className="text-center">
            <div className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl font-bold" style={{ backgroundColor: '#3a3024', border: '3px solid #a68b5b', color: '#ffd700' }}>
              1
            </div>
            <h3 className="osrs-card-title text-xl mb-2">You update your profile</h3>
            <p className="osrs-text-secondary">
              Request an update to your profile via the website or search for any player to track.
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl font-bold" style={{ backgroundColor: '#3a3024', border: '3px solid #a68b5b', color: '#ffd700' }}>
              2
            </div>
            <h3 className="osrs-card-title text-xl mb-2">We save your current stats</h3>
            <p className="osrs-text-secondary">
              We'll check your hiscores page and store your current stats on our end.
            </p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl font-bold" style={{ backgroundColor: '#3a3024', border: '3px solid #a68b5b', color: '#ffd700' }}>
              3
            </div>
            <h3 className="osrs-card-title text-xl mb-2">We calculate your progress</h3>
            <p className="osrs-text-secondary">
              Using this historical data, we can now calculate your gains, records, achievements, etc.
            </p>
          </div>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid md:grid-cols-3 gap-4 sm:gap-6">
        <div className="osrs-card">
          <h3 className="osrs-card-title text-lg sm:text-xl mb-2">📊 Skill Tracking</h3>
          <p className="osrs-text-secondary text-sm sm:text-base">
            Monitor skill levels and experience gains over time with detailed progress charts and statistics.
          </p>
        </div>
        <div className="osrs-card">
          <h3 className="osrs-card-title text-lg sm:text-xl mb-2">⚔️ Boss Progress</h3>
          <p className="osrs-text-secondary text-sm sm:text-base">
            Track boss kill counts and analyze your PvM progress with historical data and trends.
          </p>
        </div>
        <div className="osrs-card">
          <h3 className="osrs-card-title text-lg sm:text-xl mb-2">📈 Analytics</h3>
          <p className="osrs-text-secondary text-sm sm:text-base">
            Get insights into your gameplay with daily rates, progress summaries, and time estimates.
          </p>
        </div>
      </div>

      {/* Community Section */}
      <div className="osrs-card text-center">
        <h2 className="osrs-card-title text-xl sm:text-2xl md:text-3xl mb-3 sm:mb-4">Community driven</h2>
        <p className="osrs-text text-base sm:text-lg mb-4 sm:mb-6 max-w-2xl mx-auto px-2">
          OSRS Diff is a free Open Source project, meaning anyone in the community can contribute code or ideas to add new functionality.
        </p>
        <div className="flex justify-center gap-4">
          <a
            href="https://github.com/mchestr/osrsdiff"
            target="_blank"
            rel="noopener noreferrer"
            className="osrs-btn"
          >
            Contribute on GitHub
          </a>
        </div>
      </div>
    </div>
  );
};
