import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/apiClient';
import type { DatabaseStatsResponse } from '../api/models/DatabaseStatsResponse';
import { StatsGrid } from '../components/StatsGrid';
import { formatNumberLocale } from '../utils/formatters';

// Icons for stats cards - defined outside component to avoid recreation on each render
const UsersIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
  </svg>
);

const DatabaseIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
  </svg>
);

const ActiveIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const ClockIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

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
      // Silently fail for public home page - stats are optional
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/players/${encodeURIComponent(searchTerm.trim())}`);
    }
  }, [searchTerm, navigate]);

  return (
    <div>
      {/* Hero Section - TailAdmin Marketing Style */}
      <section className="relative pt-20 pb-16 sm:pt-24 sm:pb-20 lg:pt-32 lg:pb-28 bg-gradient-to-b from-secondary-50 to-white dark:from-secondary-900 dark:to-secondary-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-secondary-900 dark:text-secondary-100 tracking-tight">
              Track Your OSRS
              <span className="text-primary-600 dark:text-primary-400"> Progress</span>
            </h1>
            <p className="mt-6 text-lg sm:text-xl md:text-2xl text-secondary-600 dark:text-secondary-200 max-w-3xl mx-auto">
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
                  className="flex-1 px-6 py-4 text-base border border-secondary-300 dark:border-secondary-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent shadow-sm bg-white dark:bg-secondary-800 text-secondary-900 dark:text-secondary-100 placeholder:text-secondary-400 dark:placeholder:text-secondary-500"
                />
                <button
                  type="submit"
                  className="px-8 py-4 text-base font-semibold text-white bg-primary-600 dark:bg-primary-500 rounded-lg hover:bg-primary-700 dark:hover:bg-primary-600 transition-colors shadow-lg hover:shadow-xl"
                >
                  Search
                </button>
              </form>
            </div>
          </div>
        </div>
      </section>

      {/* Statistics Section */}
      <section className="py-16 sm:py-20 bg-white dark:bg-secondary-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <StatsGrid
            loading={loading}
            stats={
              stats
                ? [
                    {
                      title: 'Total Players',
                      value: formatNumberLocale(stats.total_players),
                      icon: <UsersIcon />,
                      color: 'primary',
                    },
                    {
                      title: 'Snapshots',
                      value: formatNumberLocale(stats.total_hiscore_records),
                      icon: <DatabaseIcon />,
                      color: 'blue',
                    },
                    {
                      title: 'Active Players',
                      value: formatNumberLocale(stats.active_players),
                      icon: <ActiveIcon />,
                      color: 'success',
                    },
                    {
                      title: 'Last 24h',
                      value: formatNumberLocale(stats.records_last_24h),
                      icon: <ClockIcon />,
                      color: 'purple',
                    },
                  ]
                : []
            }
          />
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 sm:py-20 lg:py-24 bg-secondary-50 dark:bg-secondary-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-secondary-900 dark:text-secondary-100 mb-4">
              Track your hiscores over time
            </h2>
            <p className="text-lg text-secondary-600 dark:text-secondary-200 max-w-2xl mx-auto">
              By periodically checking your hiscores, OSRS Diff can create a historical record, this allows you to:
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 lg:gap-10">
            <div className="bg-white dark:bg-secondary-900 p-8 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-secondary-200 dark:border-secondary-700">
              <div className="text-5xl mb-6 text-center">📊</div>
              <h3 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3 text-center">
                Check your gains, all-time records and collect achievements
              </h3>
              <p className="text-secondary-600 dark:text-secondary-200 text-center">
                Monitor skill levels and experience gains over time with detailed progress charts and statistics.
              </p>
            </div>
            <div className="bg-white dark:bg-secondary-900 p-8 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-secondary-200 dark:border-secondary-700">
              <div className="text-5xl mb-6 text-center">📈</div>
              <h3 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3 text-center">
                Visualise your in-game activity
              </h3>
              <p className="text-secondary-600 dark:text-secondary-200 text-center">
                Get insights into your gameplay with daily rates, progress summaries, and time estimates.
              </p>
            </div>
            <div className="bg-white dark:bg-secondary-900 p-8 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-secondary-200 dark:border-secondary-700">
              <div className="text-5xl mb-6 text-center">⚔️</div>
              <h3 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3 text-center">
                Track boss progress
              </h3>
              <p className="text-secondary-600 dark:text-secondary-200 text-center">
                Track boss kill counts and analyze your PvM progress with historical data and trends.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How it Works Section */}
      <section className="py-16 sm:py-20 lg:py-24 bg-white dark:bg-secondary-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-secondary-900 dark:text-secondary-100 mb-4">
              How does it work?
            </h2>
            <p className="text-lg text-secondary-600 dark:text-secondary-200 max-w-2xl mx-auto">
              Getting started is simple and takes just a few steps
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 lg:gap-12 max-w-5xl mx-auto">
            <div className="text-center">
              <div className="w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center text-3xl font-bold bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 border-4 border-primary-200 dark:border-primary-700 shadow-lg">
                1
              </div>
              <h3 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">You update your profile</h3>
              <p className="text-secondary-600 dark:text-secondary-200">
                Request an update to your profile via the website or search for any player to track.
              </p>
            </div>
            <div className="text-center">
              <div className="w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center text-3xl font-bold bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 border-4 border-primary-200 dark:border-primary-700 shadow-lg">
                2
              </div>
              <h3 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">We save your current stats</h3>
              <p className="text-secondary-600 dark:text-secondary-200">
                We'll check your hiscores page and store your current stats on our end.
              </p>
            </div>
            <div className="text-center">
              <div className="w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center text-3xl font-bold bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 border-4 border-primary-200 dark:border-primary-700 shadow-lg">
                3
              </div>
              <h3 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 mb-3">We calculate your progress</h3>
              <p className="text-secondary-600 dark:text-secondary-200">
                Using this historical data, we can now calculate your gains, records, achievements, etc.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-16 sm:py-20 lg:py-24 bg-secondary-50 dark:bg-secondary-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
            <div className="bg-white dark:bg-secondary-900 p-6 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-secondary-200 dark:border-secondary-700">
              <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-3">📊 Skill Tracking</h3>
              <p className="text-secondary-600 dark:text-secondary-200 text-sm">
                Monitor skill levels and experience gains over time with detailed progress charts and statistics.
              </p>
            </div>
            <div className="bg-white dark:bg-secondary-900 p-6 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-secondary-200 dark:border-secondary-700">
              <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-3">⚔️ Boss Progress</h3>
              <p className="text-secondary-600 dark:text-secondary-200 text-sm">
                Track boss kill counts and analyze your PvM progress with historical data and trends.
              </p>
            </div>
            <div className="bg-white dark:bg-secondary-900 p-6 rounded-xl shadow-sm hover:shadow-lg transition-shadow border border-secondary-200 dark:border-secondary-700">
              <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-3">📈 Analytics</h3>
              <p className="text-secondary-600 dark:text-secondary-200 text-sm">
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
            className="inline-flex items-center px-8 py-4 text-base font-semibold text-primary-600 dark:text-primary-400 bg-white dark:bg-secondary-100 rounded-lg hover:bg-secondary-50 dark:hover:bg-secondary-200 transition-colors shadow-lg hover:shadow-xl"
          >
            Contribute on GitHub
          </a>
        </div>
      </section>
    </div>
  );
};
