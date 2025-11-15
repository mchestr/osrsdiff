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
    <div>
      {/* Hero Section - TailAdmin Marketing Style */}
      <section className="relative pt-20 pb-16 sm:pt-24 sm:pb-20 lg:pt-32 lg:pb-28 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-gray-900 tracking-tight">
              Track Your OSRS
              <span className="text-primary-600"> Progress</span>
            </h1>
            <p className="mt-6 text-lg sm:text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto">
              The open source Old School RuneScape player progress tracker. Monitor your skills, track boss kills, and visualize your journey.
            </p>

            {/* Search Form - Hero CTA */}
            <div className="mt-10 max-w-2xl mx-auto">
              <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
                <input
                  type="text"
                  placeholder="Search for a player by username..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 px-6 py-4 text-base border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent shadow-sm"
                />
                <button
                  type="submit"
                  className="px-8 py-4 text-base font-semibold text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors shadow-lg hover:shadow-xl"
                >
                  Search
                </button>
              </form>
            </div>
          </div>
        </div>
      </section>

      {/* Statistics Section */}
      <section className="py-16 sm:py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 lg:gap-8">
            {loading ? (
              <>
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="text-center p-6 bg-gray-50 rounded-xl">
                    <div className="text-3xl md:text-4xl font-bold mb-2 text-gray-300">...</div>
                    <div className="text-sm text-gray-500">Loading...</div>
                  </div>
                ))}
              </>
            ) : stats ? (
              <>
                <div className="text-center p-6 bg-gradient-to-br from-primary-50 to-primary-100 rounded-xl border border-primary-200 hover:shadow-lg transition-shadow">
                  <div className="text-3xl md:text-4xl font-bold mb-2 text-primary-600">
                    {formatNumber(stats.total_players)}
                  </div>
                  <div className="text-sm font-medium text-gray-700">Players</div>
                </div>
                <div className="text-center p-6 bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl border border-blue-200 hover:shadow-lg transition-shadow">
                  <div className="text-3xl md:text-4xl font-bold mb-2 text-blue-600">
                    {formatNumber(stats.total_hiscore_records)}
                  </div>
                  <div className="text-sm font-medium text-gray-700">Snapshots</div>
                </div>
                <div className="text-center p-6 bg-gradient-to-br from-success-50 to-success-100 rounded-xl border border-success-200 hover:shadow-lg transition-shadow">
                  <div className="text-3xl md:text-4xl font-bold mb-2 text-success-600">
                    {formatNumber(stats.active_players)}
                  </div>
                  <div className="text-sm font-medium text-gray-700">Active</div>
                </div>
                <div className="text-center p-6 bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl border border-purple-200 hover:shadow-lg transition-shadow">
                  <div className="text-3xl md:text-4xl font-bold mb-2 text-purple-600">
                    {formatNumber(stats.records_last_24h)}
                  </div>
                  <div className="text-sm font-medium text-gray-700">Last 24h</div>
                </div>
              </>
            ) : null}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 sm:py-20 lg:py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Track your hiscores over time
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              By periodically checking your hiscores, OSRS Diff can create a historical record, this allows you to:
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 lg:gap-10">
            <div className="bg-white p-8 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-gray-100">
              <div className="text-5xl mb-6 text-center">📊</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3 text-center">
                Check your gains, all-time records and collect achievements
              </h3>
              <p className="text-gray-600 text-center">
                Monitor skill levels and experience gains over time with detailed progress charts and statistics.
              </p>
            </div>
            <div className="bg-white p-8 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-gray-100">
              <div className="text-5xl mb-6 text-center">📈</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3 text-center">
                Visualise your in-game activity
              </h3>
              <p className="text-gray-600 text-center">
                Get insights into your gameplay with daily rates, progress summaries, and time estimates.
              </p>
            </div>
            <div className="bg-white p-8 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-gray-100">
              <div className="text-5xl mb-6 text-center">⚔️</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3 text-center">
                Track boss progress
              </h3>
              <p className="text-gray-600 text-center">
                Track boss kill counts and analyze your PvM progress with historical data and trends.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How it Works Section */}
      <section className="py-16 sm:py-20 lg:py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              How does it work?
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Getting started is simple and takes just a few steps
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 lg:gap-12 max-w-5xl mx-auto">
            <div className="text-center">
              <div className="w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center text-3xl font-bold bg-primary-100 text-primary-600 border-4 border-primary-200 shadow-lg">
                1
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">You update your profile</h3>
              <p className="text-gray-600">
                Request an update to your profile via the website or search for any player to track.
              </p>
            </div>
            <div className="text-center">
              <div className="w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center text-3xl font-bold bg-primary-100 text-primary-600 border-4 border-primary-200 shadow-lg">
                2
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">We save your current stats</h3>
              <p className="text-gray-600">
                We'll check your hiscores page and store your current stats on our end.
              </p>
            </div>
            <div className="text-center">
              <div className="w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center text-3xl font-bold bg-primary-100 text-primary-600 border-4 border-primary-200 shadow-lg">
                3
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-3">We calculate your progress</h3>
              <p className="text-gray-600">
                Using this historical data, we can now calculate your gains, records, achievements, etc.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-16 sm:py-20 lg:py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
            <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">📊 Skill Tracking</h3>
              <p className="text-gray-600 text-sm">
                Monitor skill levels and experience gains over time with detailed progress charts and statistics.
              </p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">⚔️ Boss Progress</h3>
              <p className="text-gray-600 text-sm">
                Track boss kill counts and analyze your PvM progress with historical data and trends.
              </p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-gray-100">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">📈 Analytics</h3>
              <p className="text-gray-600 text-sm">
                Get insights into your gameplay with daily rates, progress summaries, and time estimates.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 sm:py-20 lg:py-24 bg-gradient-to-r from-primary-600 to-primary-700">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Community driven
          </h2>
          <p className="text-lg sm:text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
            OSRS Diff is a free Open Source project, meaning anyone in the community can contribute code or ideas to add new functionality.
          </p>
          <a
            href="https://github.com/mchestr/osrsdiff"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-8 py-4 text-base font-semibold text-primary-600 bg-white rounded-lg hover:bg-gray-50 transition-colors shadow-lg hover:shadow-xl"
          >
            Contribute on GitHub
          </a>
        </div>
      </section>
    </div>
  );
};
