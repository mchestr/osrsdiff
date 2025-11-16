import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorDisplay } from '../components/ErrorDisplay';
import { formatNumberLocale } from '../utils/formatters';
import { OSRS_SKILL_ORDER } from '../utils/osrs';
import { SKILL_ICONS } from '../utils/skillIcons';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? '' : '');

interface LeaderboardEntry {
  rank: number;
  username: string;
  fetched_at?: string;
}

interface OverallExpEntry extends LeaderboardEntry {
  overall_experience?: number;
  overall_level?: number;
  overall_rank?: number;
}

interface TotalLevelEntry extends LeaderboardEntry {
  overall_level?: number;
  overall_experience?: number;
  overall_rank?: number;
}

interface SkillEntry extends LeaderboardEntry {
  skill_experience?: number;
  skill_level?: number;
  skill_rank?: number;
}

type LeaderboardType = 'overall' | 'skill';

export const Leaderboard: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<LeaderboardType>('overall');
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [overallExpData, setOverallExpData] = useState<OverallExpEntry[]>([]);
  const [totalLevelData, setTotalLevelData] = useState<TotalLevelEntry[]>([]);
  const [skillData, setSkillData] = useState<SkillEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [limit] = useState(100);
  const [sortBy, setSortBy] = useState<'exp' | 'level'>('exp');

  const fetchOverallExp = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/leaderboard/overall-exp`, {
        params: { limit },
      });
      setOverallExpData(response.data.leaderboard || []);
    } catch (err) {
      console.error('Error fetching overall EXP leaderboard:', err);
      setError('Failed to load overall EXP leaderboard');
    }
  }, [limit]);

  const fetchTotalLevel = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/leaderboard/total-level`, {
        params: { limit },
      });
      setTotalLevelData(response.data.leaderboard || []);
    } catch (err) {
      console.error('Error fetching total level leaderboard:', err);
      setError('Failed to load total level leaderboard');
    }
  }, [limit]);

  const fetchSkillLeaderboard = useCallback(async (skillName: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/leaderboard/skill/${skillName}`, {
        params: { limit },
      });
      setSkillData(response.data.leaderboard || []);
    } catch (err) {
      console.error(`Error fetching ${skillName} leaderboard:`, err);
      setError(`Failed to load ${skillName} leaderboard`);
    }
  }, [limit]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        await Promise.all([
          fetchOverallExp(),
          fetchTotalLevel(),
        ]);
      } catch (err) {
        console.error('Error loading leaderboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [fetchOverallExp, fetchTotalLevel]);

  useEffect(() => {
    if (selectedSkill && activeTab === 'skill') {
      fetchSkillLeaderboard(selectedSkill);
    }
  }, [selectedSkill, activeTab, fetchSkillLeaderboard]);

  const handlePlayerClick = (username: string) => {
    navigate(`/players/${encodeURIComponent(username)}`);
  };

  const getSkillDisplayName = (skillName: string): string => {
    return skillName
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  if (loading) {
    return <LoadingSpinner message="Loading leaderboards..." fullScreen />;
  }

  if (error && !overallExpData.length && !totalLevelData.length) {
    return <ErrorDisplay error={error} />;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl sm:text-4xl font-bold text-secondary-900 dark:text-secondary-100 mb-2">
          Leaderboards
        </h1>
        <p className="text-secondary-600 dark:text-secondary-200">
          Top players across all tracked skills and statistics
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-secondary-200 dark:border-secondary-700">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => {
              setActiveTab('overall');
              setSelectedSkill(null);
            }}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'overall'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-secondary-500 hover:text-secondary-700 hover:border-secondary-300 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
          >
            Overall
          </button>
          <button
            onClick={() => {
              setActiveTab('skill');
              if (!selectedSkill) {
                setSelectedSkill(OSRS_SKILL_ORDER[0]);
              }
            }}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'skill'
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-secondary-500 hover:text-secondary-700 hover:border-secondary-300 dark:text-secondary-400 dark:hover:text-secondary-300'
            }`}
          >
            Skills
          </button>
        </nav>
      </div>

      {/* Skill selector for skill tab */}
      {activeTab === 'skill' && (
        <div className="mb-6">
          <div className="flex flex-wrap gap-2">
            {OSRS_SKILL_ORDER.map((skill) => {
              const icon = SKILL_ICONS[skill];
              return (
                <button
                  key={skill}
                  onClick={() => setSelectedSkill(skill)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                    selectedSkill === skill
                      ? 'bg-primary-50 dark:bg-primary-900/20 border-primary-500 text-primary-700 dark:text-primary-300'
                      : 'bg-white dark:bg-secondary-800 border-secondary-300 dark:border-secondary-600 text-secondary-700 dark:text-secondary-300 hover:bg-secondary-50 dark:hover:bg-secondary-700'
                  }`}
                >
                  {icon && icon !== '⚓' && (
                    <img src={icon} alt={skill} className="w-5 h-5" />
                  )}
                  <span className="capitalize">{getSkillDisplayName(skill)}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Leaderboard Content */}
      <div className="bg-white dark:bg-secondary-900 rounded-lg shadow-sm border border-secondary-200 dark:border-secondary-700 overflow-hidden">
        {activeTab === 'overall' && (
          <>
            {/* Sort toggle */}
            <div className="px-6 py-4 border-b border-secondary-200 dark:border-secondary-700 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100">
                Overall Leaderboard
              </h2>
              <div className="flex gap-2">
                <button
                  onClick={() => setSortBy('exp')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    sortBy === 'exp'
                      ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 border border-primary-500'
                      : 'bg-white dark:bg-secondary-800 border border-secondary-300 dark:border-secondary-600 text-secondary-700 dark:text-secondary-300 hover:bg-secondary-50 dark:hover:bg-secondary-700'
                  }`}
                >
                  Sort by EXP
                </button>
                <button
                  onClick={() => setSortBy('level')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    sortBy === 'level'
                      ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 border border-primary-500'
                      : 'bg-white dark:bg-secondary-800 border border-secondary-300 dark:border-secondary-600 text-secondary-700 dark:text-secondary-300 hover:bg-secondary-50 dark:hover:bg-secondary-700'
                  }`}
                >
                  Sort by Level
                </button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-secondary-200 dark:divide-secondary-700">
                <thead className="bg-secondary-50 dark:bg-secondary-800">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                      Rank
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                      Player
                    </th>
                    <th className={`px-6 py-3 text-right text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider ${sortBy === 'exp' ? 'font-semibold' : ''}`}>
                      Total EXP
                    </th>
                    <th className={`px-6 py-3 text-right text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider ${sortBy === 'level' ? 'font-semibold' : ''}`}>
                      Total Level
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                      OSRS Rank
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-secondary-900 divide-y divide-secondary-200 dark:divide-secondary-700">
                  {(sortBy === 'exp' ? overallExpData : totalLevelData).map((entry) => (
                    <tr
                      key={entry.username}
                      onClick={() => handlePlayerClick(entry.username)}
                      className="hover:bg-secondary-50 dark:hover:bg-secondary-800 cursor-pointer transition-colors"
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-secondary-900 dark:text-secondary-100">
                        #{entry.rank}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-900 dark:text-secondary-100">
                        {entry.username}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm text-right text-secondary-900 dark:text-secondary-100 ${sortBy === 'exp' ? 'font-semibold' : ''}`}>
                        {entry.overall_experience
                          ? formatNumberLocale(entry.overall_experience)
                          : '-'}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm text-right text-secondary-900 dark:text-secondary-100 ${sortBy === 'level' ? 'font-semibold' : ''}`}>
                        {entry.overall_level ?? '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-secondary-500 dark:text-secondary-400">
                        {entry.overall_rank ? `#${formatNumberLocale(entry.overall_rank)}` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {activeTab === 'skill' && selectedSkill && (
          <div className="overflow-x-auto">
            <div className="px-6 py-4 border-b border-secondary-200 dark:border-secondary-700">
              <h2 className="text-xl font-semibold text-secondary-900 dark:text-secondary-100 flex items-center gap-2">
                {SKILL_ICONS[selectedSkill] && SKILL_ICONS[selectedSkill] !== '⚓' && (
                  <img src={SKILL_ICONS[selectedSkill]} alt={selectedSkill} className="w-6 h-6" />
                )}
                {getSkillDisplayName(selectedSkill)} Leaderboard
              </h2>
            </div>
            <table className="min-w-full divide-y divide-secondary-200 dark:divide-secondary-700">
              <thead className="bg-secondary-50 dark:bg-secondary-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                    Rank
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                    Player
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                    Level
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                    Experience
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-secondary-500 dark:text-secondary-400 uppercase tracking-wider">
                    OSRS Rank
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-secondary-900 divide-y divide-secondary-200 dark:divide-secondary-700">
                {skillData.length > 0 ? (
                  skillData.map((entry) => (
                    <tr
                      key={entry.username}
                      onClick={() => handlePlayerClick(entry.username)}
                      className="hover:bg-secondary-50 dark:hover:bg-secondary-800 cursor-pointer transition-colors"
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-secondary-900 dark:text-secondary-100">
                        #{entry.rank}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-900 dark:text-secondary-100">
                        {entry.username}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-secondary-900 dark:text-secondary-100 font-semibold">
                        {entry.skill_level ?? '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-secondary-900 dark:text-secondary-100">
                        {entry.skill_experience
                          ? formatNumberLocale(entry.skill_experience)
                          : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-secondary-500 dark:text-secondary-400">
                        {entry.skill_rank ? `#${formatNumberLocale(entry.skill_rank)}` : '-'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-sm text-secondary-500 dark:text-secondary-400">
                      Loading {getSkillDisplayName(selectedSkill)} leaderboard...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

