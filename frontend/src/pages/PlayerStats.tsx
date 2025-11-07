import { format } from 'date-fns';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { PlayerStatsResponse } from '../api/models/PlayerStatsResponse';
import type { ProgressAnalysisResponse } from '../api/models/ProgressAnalysisResponse';
import { api } from '../lib/apiClient';

export const PlayerStats: React.FC = () => {
  const { username } = useParams<{ username: string }>();
  const [stats, setStats] = useState<PlayerStatsResponse | null>(null);
  const [progress, setProgress] = useState<ProgressAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      if (!username) return;

      try {
        setLoading(true);
        const [statsRes, progressRes] = await Promise.all([
          api.StatisticsService.getPlayerStatsApiV1PlayersUsernameStatsGet(username),
          api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 30).catch(() => null),
        ]);

        setStats(statsRes);
        if (progressRes) {
          setProgress(progressRes);
        }
      } catch (err: any) {
        setError(err.body?.detail || err.message || 'Failed to load player stats');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [username]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="card">
        <div className="text-red-600">{error || 'Player not found'}</div>
      </div>
    );
  }

  const skillNames = Object.keys(stats.skills || {});
  const bossNames = Object.keys(stats.bosses || {});

  // Prepare data for charts
  const topSkills = skillNames
    .map((name) => {
      const skillData = stats.skills?.[name];
      if (!skillData || typeof skillData !== 'object') return null;
      return {
        name: name.charAt(0).toUpperCase() + name.slice(1),
        level: (skillData as any).level || 0,
        experience: (skillData as any).experience || 0,
      };
    })
    .filter((skill): skill is { name: string; level: number; experience: number } => skill !== null)
    .sort((a, b) => b.level - a.level)
    .slice(0, 10);

  const topBosses = bossNames
    .map((name) => {
      const bossData = stats.bosses?.[name];
      if (!bossData || typeof bossData !== 'object') return null;
      // Boss data structure: {rank: number | null, kc: number | null}
      // The API uses "kc" for kill count
      const kills = (bossData as any).kc ?? (bossData as any).kill_count ?? (bossData as any).kills ?? 0;
      return {
        name: name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
        kills: typeof kills === 'number' && kills !== null ? kills : 0,
      };
    })
    .filter((boss): boss is { name: string; kills: number } => boss !== null && boss.kills > 0)
    .sort((a, b) => b.kills - a.kills)
    .slice(0, 10);

  const progressData = progress
    ? Object.entries(progress.progress.experience_gained)
        .map(([skill, exp]: [string, number]) => ({
          skill: skill.charAt(0).toUpperCase() + skill.slice(1),
          experience: exp,
          levels: progress.progress.levels_gained[skill] || 0,
        }))
        .filter((item) => item.experience > 0)
        .sort((a, b) => b.experience - a.experience)
        .slice(0, 10)
    : [];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">
          {stats.username}
        </h1>
        {stats.fetched_at && (
          <p className="text-sm text-gray-500">
            Last updated: {format(new Date(stats.fetched_at), 'PPpp')}
          </p>
        )}
      </div>

      {/* Overall Stats */}
      {stats.overall && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Total Level</h3>
            <p className="text-3xl font-bold text-primary-600">{stats.overall.level ?? 'N/A'}</p>
          </div>
          <div className="card">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Total Experience</h3>
            <p className="text-3xl font-bold text-primary-600">
              {stats.overall.experience?.toLocaleString() ?? 'N/A'}
            </p>
          </div>
          <div className="card">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Combat Level</h3>
            <p className="text-3xl font-bold text-primary-600">{stats.combat_level ?? 'N/A'}</p>
          </div>
        </div>
      )}

      {/* Progress Summary */}
      {progress && (
        <div className="card">
          <h2 className="text-xl font-bold mb-4">30-Day Progress</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">Total Experience Gained</h3>
              <p className="text-2xl font-bold">
                {Object.values(progress.progress.experience_gained)
                  .reduce((sum: number, exp: number) => sum + exp, 0)
                  .toLocaleString()}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">Total Levels Gained</h3>
              <p className="text-2xl font-bold">
                {Object.values(progress.progress.levels_gained)
                  .reduce((sum: number, levels: number) => sum + levels, 0)}
              </p>
            </div>
          </div>
          {progressData.length > 0 && (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={progressData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="skill" angle={-45} textAnchor="end" height={100} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="experience" fill="#0ea5e9" name="Experience Gained" />
                  <Bar dataKey="levels" fill="#10b981" name="Levels Gained" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Top Skills */}
      <div className="card">
        <h2 className="text-xl font-bold mb-4">Top Skills</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={topSkills} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={100} />
              <Tooltip />
              <Legend />
              <Bar dataKey="level" fill="#0ea5e9" name="Level" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Bosses */}
      {topBosses.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-bold mb-4">Top Bosses</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topBosses} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={100} />
                <Tooltip />
                <Legend />
                <Bar dataKey="kills" fill="#10b981" name="Kills" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Skills Grid */}
      <div className="card">
        <h2 className="text-xl font-bold mb-4">All Skills</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {skillNames.map((skill) => {
            const skillData = stats.skills?.[skill];
            if (!skillData || typeof skillData !== 'object') return null;
            const level = (skillData as any).level || 0;
            const experience = (skillData as any).experience || 0;
            return (
              <div key={skill} className="p-3 bg-gray-50 rounded-lg">
                <h3 className="text-sm font-medium text-gray-700 mb-1">
                  {skill.charAt(0).toUpperCase() + skill.slice(1)}
                </h3>
                <p className="text-lg font-bold text-primary-600">{level}</p>
                <p className="text-xs text-gray-500">{experience.toLocaleString()} XP</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

