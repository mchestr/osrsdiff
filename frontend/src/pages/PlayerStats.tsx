import { format } from 'date-fns';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api/apiClient';
import type { PlayerStatsResponse } from '../api/models/PlayerStatsResponse';
import type { ProgressAnalysisResponse } from '../api/models/ProgressAnalysisResponse';

// OSRS skill order matching the game interface (6 columns x 4 rows)
const OSRS_SKILL_ORDER = [
  'attack', 'hitpoints', 'mining', 'strength', 'agility', 'smithing',
  'defence', 'herblore', 'fishing', 'ranged', 'thieving', 'cooking',
  'prayer', 'crafting', 'firemaking', 'magic', 'fletching', 'woodcutting',
  'runecraft', 'slayer', 'farming', 'construction', 'hunter', 'sailing',
];

// Skill icons (using Unicode/emoji representations)
const SKILL_ICONS: Record<string, string> = {
  attack: '⚔️',
  hitpoints: '❤️',
  mining: '⛏️',
  strength: '💪',
  agility: '🏃',
  smithing: '🔨',
  defence: '🛡️',
  herblore: '🌿',
  fishing: '🐟',
  ranged: '🏹',
  thieving: '🎭',
  cooking: '🍲',
  prayer: '⭐',
  crafting: '🔧',
  firemaking: '🔥',
  magic: '🔮',
  fletching: '🏹',
  woodcutting: '🪵',
  runecraft: '✨',
  slayer: '💀',
  farming: '🌾',
  construction: '🏗️',
  hunter: '🐾',
  sailing: '⚓',
};

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
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load player stats';
        const errorDetail = (err as { body?: { detail?: string } })?.body?.detail;
        setError(errorDetail || errorMessage);
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

  // Type definitions for skill and boss data
  interface SkillData {
    level?: number;
    experience?: number;
    rank?: number;
  }

  interface BossData {
    kc?: number | null;
    kill_count?: number | null;
    kills?: number | null;
    rank?: number | null;
  }

  // Get skills in OSRS order, filtering to only include skills that exist
  const orderedSkills = OSRS_SKILL_ORDER
    .map((skillName) => {
      const skillData = stats.skills?.[skillName] as SkillData | undefined;
      if (!skillData || typeof skillData !== 'object') return null;
      return {
        name: skillName,
        displayName: skillName.charAt(0).toUpperCase() + skillName.slice(1),
        level: skillData.level ?? 0,
        experience: skillData.experience ?? 0,
        maxLevel: 99, // OSRS max level is 99 for most skills, but some have different maxes
      };
    })
    .filter((skill): skill is { name: string; displayName: string; level: number; experience: number; maxLevel: number } => skill !== null);

  // Prepare data for charts
  const topSkills = skillNames
    .map((name) => {
      const skillData = stats.skills?.[name] as SkillData | undefined;
      if (!skillData || typeof skillData !== 'object') return null;
      return {
        name: name.charAt(0).toUpperCase() + name.slice(1),
        level: skillData.level ?? 0,
        experience: skillData.experience ?? 0,
      };
    })
    .filter((skill): skill is { name: string; level: number; experience: number } => skill !== null)
    .sort((a, b) => b.level - a.level)
    .slice(0, 10);

  const topBosses = bossNames
    .map((name) => {
      const bossData = stats.bosses?.[name] as BossData | undefined;
      if (!bossData || typeof bossData !== 'object') return null;
      // Boss data structure: {rank: number | null, kc: number | null}
      // The API uses "kc" for kill count
      const kills = bossData.kc ?? bossData.kill_count ?? bossData.kills ?? 0;
      return {
        name: name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
        kills: typeof kills === 'number' && kills !== null ? kills : 0,
      };
    })
    .filter((boss): boss is { name: string; kills: number } => boss !== null && boss.kills > 0)
    .sort((a, b) => b.kills - a.kills)
    .slice(0, 10);

  const progressData = progress
    ? (Object.entries(progress.progress.experience_gained) as [string, number][])
        .map(([skill, exp]) => ({
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* OSRS Skills Grid - Main Feature */}
        <div className="lg:col-span-2">
          <div className="osrs-skills-panel">
            <div className="osrs-skills-grid">
              {orderedSkills.map((skill) => {
                const icon = SKILL_ICONS[skill.name] || '❓';
                const maxLevel = skill.name === 'sailing' ? 1 : 99; // Sailing has max level 1
                return (
                  <div key={skill.name} className="osrs-skill-cell">
                    <div className="osrs-skill-icon">{icon}</div>
                    <div className="osrs-skill-level">
                      {skill.level}/{maxLevel}
                    </div>
                    <div className="osrs-skill-name">{skill.displayName}</div>
                  </div>
                );
              })}
            </div>
            <div className="osrs-total-level">
              Total level: {stats.overall?.level ?? 0}
            </div>
          </div>
        </div>

        {/* Overall Stats Sidebar */}
        <div className="space-y-4">
          {stats.overall && (
            <div className="card">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Total Level</h3>
              <p className="text-3xl font-bold text-primary-600">{stats.overall.level ?? 'N/A'}</p>
            </div>
          )}
          {stats.overall && (
            <div className="card">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Total Experience</h3>
              <p className="text-3xl font-bold text-primary-600">
                {stats.overall.experience?.toLocaleString() ?? 'N/A'}
              </p>
            </div>
          )}
          {stats.combat_level && (
            <div className="card">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Combat Level</h3>
              <p className="text-3xl font-bold text-primary-600">{stats.combat_level}</p>
            </div>
          )}
        </div>
      </div>

      {/* Progress Summary */}
      {progress && (
        <div className="card">
          <h2 className="text-xl font-bold mb-4">30-Day Progress</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">Total Experience Gained</h3>
              <p className="text-2xl font-bold">
                {(Object.values(progress.progress.experience_gained) as number[])
                  .reduce((sum: number, exp: number) => sum + exp, 0)
                  .toLocaleString()}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">Total Levels Gained</h3>
              <p className="text-2xl font-bold">
                {(Object.values(progress.progress.levels_gained) as number[])
                  .reduce((sum: number, levels: number) => sum + levels, 0)}
              </p>
            </div>
          </div>
          {progressData.length > 0 && (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={progressData} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="skill"
                    angle={-45}
                    textAnchor="end"
                    height={120}
                    tick={{ fontSize: 12, fill: '#374151' }}
                    interval={0}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: '#374151' }}
                    label={{ value: 'Experience', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fill: '#374151' } }}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                  />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  <Bar dataKey="experience" fill="#0ea5e9" name="Experience Gained" />
                  <Bar dataKey="levels" fill="#10b981" name="Levels Gained" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Top Skills Chart */}
      <div className="card">
        <h2 className="text-xl font-bold mb-4">Top Skills by Level</h2>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={topSkills} layout="vertical" margin={{ top: 5, right: 30, left: 120, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                type="number"
                tick={{ fontSize: 12, fill: '#374151' }}
                label={{ value: 'Level', position: 'insideBottom', offset: -5, style: { textAnchor: 'middle', fill: '#374151' } }}
              />
              <YAxis
                dataKey="name"
                type="category"
                width={110}
                tick={{ fontSize: 12, fill: '#374151' }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
              />
              <Legend wrapperStyle={{ paddingTop: '20px' }} />
              <Bar dataKey="level" fill="#0ea5e9" name="Level" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Bosses Chart */}
      {topBosses.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-bold mb-4">Top Bosses by Kill Count</h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topBosses} layout="vertical" margin={{ top: 5, right: 30, left: 120, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  type="number"
                  tick={{ fontSize: 12, fill: '#374151' }}
                  label={{ value: 'Kill Count', position: 'insideBottom', offset: -5, style: { textAnchor: 'middle', fill: '#374151' } }}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={110}
                  tick={{ fontSize: 12, fill: '#374151' }}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Bar dataKey="kills" fill="#10b981" name="Kills" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

