import { format } from 'date-fns';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api/apiClient';
import type { PlayerStatsResponse } from '../api/models/PlayerStatsResponse';
import type { ProgressAnalysisResponse } from '../api/models/ProgressAnalysisResponse';
import type { SkillProgressResponse } from '../api/models/SkillProgressResponse';

// Import local skill icons
import agilityIcon from '../assets/images/skill-icons/agility-icon.png';
import attackIcon from '../assets/images/skill-icons/attack-icon.png';
import constructionIcon from '../assets/images/skill-icons/construction-icon.png';
import cookingIcon from '../assets/images/skill-icons/cooking-icon.png';
import craftingIcon from '../assets/images/skill-icons/crafting-icon.png';
import defenceIcon from '../assets/images/skill-icons/defence-icon.png';
import farmingIcon from '../assets/images/skill-icons/farming-icon.png';
import firemakingIcon from '../assets/images/skill-icons/firemaking-icon.png';
import fishingIcon from '../assets/images/skill-icons/fishing-icon.png';
import fletchingIcon from '../assets/images/skill-icons/fletching-icon.png';
import herbloreIcon from '../assets/images/skill-icons/herblore-icon.png';
import hitpointsIcon from '../assets/images/skill-icons/hitpoints-icon.png';
import hunterIcon from '../assets/images/skill-icons/hunter-icon.png';
import magicIcon from '../assets/images/skill-icons/magic-icon.png';
import miningIcon from '../assets/images/skill-icons/mining-icon.png';
import prayerIcon from '../assets/images/skill-icons/prayer-icon.png';
import rangedIcon from '../assets/images/skill-icons/ranged-icon.png';
import runecraftIcon from '../assets/images/skill-icons/runecraft-icon.png';
import slayerIcon from '../assets/images/skill-icons/slayer-icon.png';
import smithingIcon from '../assets/images/skill-icons/smithing-icon.png';
import strengthIcon from '../assets/images/skill-icons/strength-icon.png';
import thievingIcon from '../assets/images/skill-icons/thieving-icon.png';
import woodcuttingIcon from '../assets/images/skill-icons/woodcutting-icon.png';

// OSRS skill order matching the game interface (3 columns x 8 rows)
const OSRS_SKILL_ORDER = [
  'attack', 'hitpoints', 'mining',
  'strength', 'agility', 'smithing',
  'defence', 'herblore', 'fishing',
  'ranged', 'thieving', 'cooking',
  'prayer', 'crafting', 'firemaking',
  'magic', 'fletching', 'woodcutting',
  'runecraft', 'slayer', 'farming',
  'construction', 'hunter', 'sailing',
];

// Local OSRS skill icons (cached from wiki)
const SKILL_ICONS: Record<string, string> = {
  attack: attackIcon,
  hitpoints: hitpointsIcon,
  mining: miningIcon,
  strength: strengthIcon,
  agility: agilityIcon,
  smithing: smithingIcon,
  defence: defenceIcon,
  herblore: herbloreIcon,
  fishing: fishingIcon,
  ranged: rangedIcon,
  thieving: thievingIcon,
  cooking: cookingIcon,
  prayer: prayerIcon,
  crafting: craftingIcon,
  firemaking: firemakingIcon,
  magic: magicIcon,
  fletching: fletchingIcon,
  woodcutting: woodcuttingIcon,
  runecraft: runecraftIcon,
  slayer: slayerIcon,
  farming: farmingIcon,
  construction: constructionIcon,
  hunter: hunterIcon,
  sailing: '⚓', // Sailing is newer, may not have an icon on the wiki yet
};

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

// OSRS experience table - experience required for each level
const getExpForLevel = (level: number): number => {
  if (level <= 1) return 0;
  let total = 0;
  for (let i = 1; i < level; i++) {
    total += Math.floor(i + 300 * Math.pow(2, i / 7));
  }
  return Math.floor(total / 4);
};

// Calculate experience needed for next level
const getExpToNextLevel = (currentLevel: number, currentExp: number): number => {
  if (currentLevel >= 99) return 0;
  const nextLevelExp = getExpForLevel(currentLevel + 1);
  return Math.max(0, nextLevelExp - currentExp);
};

// Calculate experience needed for max level (99)
const getExpToMax = (currentLevel: number, currentExp: number): number => {
  if (currentLevel >= 99) return 0;
  const maxLevelExp = getExpForLevel(99);
  return Math.max(0, maxLevelExp - currentExp);
};

// Format time duration
const formatDuration = (days: number): string => {
  if (days < 0) return 'N/A';
  if (days < 1) {
    const hours = Math.floor(days * 24);
    if (hours < 1) {
      const minutes = Math.floor(days * 24 * 60);
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    }
    return `${hours} hour${hours !== 1 ? 's' : ''}`;
  }
  if (days < 7) {
    return `${Math.floor(days)} day${Math.floor(days) !== 1 ? 's' : ''}`;
  }
  if (days < 30) {
    const weeks = Math.floor(days / 7);
    const remainingDays = Math.floor(days % 7);
    if (remainingDays === 0) {
      return `${weeks} week${weeks !== 1 ? 's' : ''}`;
    }
    return `${weeks} week${weeks !== 1 ? 's' : ''}, ${remainingDays} day${remainingDays !== 1 ? 's' : ''}`;
  }
  if (days < 365) {
    const months = Math.floor(days / 30);
    const remainingDays = Math.floor(days % 30);
    if (remainingDays === 0) {
      return `${months} month${months !== 1 ? 's' : ''}`;
    }
    return `${months} month${months !== 1 ? 's' : ''}, ${remainingDays} day${remainingDays !== 1 ? 's' : ''}`;
  }
  const years = Math.floor(days / 365);
  const remainingDays = Math.floor(days % 365);
  if (remainingDays === 0) {
    return `${years} year${years !== 1 ? 's' : ''}`;
  }
  const months = Math.floor(remainingDays / 30);
  return `${years} year${years !== 1 ? 's' : ''}, ${months} month${months !== 1 ? 's' : ''}`;
};

export const PlayerStats: React.FC = () => {
  const { username } = useParams<{ username: string }>();
  const [stats, setStats] = useState<PlayerStatsResponse | null>(null);
  const [progress, setProgress] = useState<ProgressAnalysisResponse | null>(null);
  const [progressDay, setProgressDay] = useState<ProgressAnalysisResponse | null>(null);
  const [progressWeek, setProgressWeek] = useState<ProgressAnalysisResponse | null>(null);
  const [progressMonth, setProgressMonth] = useState<ProgressAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [skillProgress, setSkillProgress] = useState<SkillProgressResponse | null>(null);
  const [skillProgressLoading, setSkillProgressLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!username) return;

      try {
        setLoading(true);
        const [statsRes, progressDayRes, progressWeekRes, progressMonthRes] = await Promise.all([
          api.StatisticsService.getPlayerStatsApiV1PlayersUsernameStatsGet(username),
          api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 1).catch(() => null),
          api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 7).catch(() => null),
          api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 30).catch(() => null),
        ]);

        setStats(statsRes);
        setProgressDay(progressDayRes);
        setProgressWeek(progressWeekRes);
        setProgressMonth(progressMonthRes);
        if (progressMonthRes) {
          setProgress(progressMonthRes);
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

  const handleSkillClick = async (skillName: string) => {
    if (!username) return;

    setSelectedSkill(skillName);
    setSkillProgressLoading(true);

    try {
      const skillData = await api.HistoryService.getSkillProgressApiV1PlayersUsernameHistorySkillsSkillGet(
        username,
        skillName,
        90 // Get 90 days of history
      );
      setSkillProgress(skillData);
    } catch (err: unknown) {
      console.error('Failed to load skill progress:', err);
      setSkillProgress(null);
    } finally {
      setSkillProgressLoading(false);
    }
  };

  const closeSkillModal = () => {
    setSelectedSkill(null);
    setSkillProgress(null);
  };

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

  const bossNames = Object.keys(stats.bosses || {});

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
        <div>
          <div className="osrs-skills-panel">
            <div className="osrs-skills-grid">
              {orderedSkills.map((skill) => {
                const iconUrl = SKILL_ICONS[skill.name];
                const maxLevel = skill.name === 'sailing' ? 1 : 99; // Sailing has max level 1
                return (
                  <div
                    key={skill.name}
                    className="osrs-skill-cell cursor-pointer hover:opacity-80 transition-opacity"
                    onClick={() => handleSkillClick(skill.name)}
                    title={`Click to view ${skill.displayName} details`}
                  >
                    <div className="osrs-skill-icon">
                      {iconUrl && iconUrl !== '⚓' ? (
                        <img
                          src={iconUrl}
                          alt={skill.displayName}
                          className="osrs-skill-icon-img"
                          onError={(e) => {
                            // Fallback to emoji if image fails to load
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                            if (!target.parentElement?.querySelector('.osrs-skill-icon-fallback')) {
                              const fallback = document.createElement('span');
                              fallback.textContent = '❓';
                              fallback.className = 'osrs-skill-icon-fallback';
                              target.parentElement?.appendChild(fallback);
                            }
                          }}
                        />
                      ) : (
                        <span className="osrs-skill-icon-fallback">{iconUrl || '❓'}</span>
                      )}
                    </div>
                    <div className="osrs-skill-level">
                      {skill.level}/{maxLevel}
                    </div>
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

        {/* Most Progressed Skills */}
        <div className="space-y-4">
          <MostProgressedSkills
            title="Last Day"
            progress={progressDay}
            skillIcons={SKILL_ICONS}
          />
          <MostProgressedSkills
            title="Last Week"
            progress={progressWeek}
            skillIcons={SKILL_ICONS}
          />
          <MostProgressedSkills
            title="Last Month"
            progress={progressMonth}
            skillIcons={SKILL_ICONS}
          />
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

      {/* Skill Detail Modal */}
      {selectedSkill && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={closeSkillModal}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {skillProgressLoading ? (
              <div className="p-8 text-center">
                <div className="text-xl">Loading skill details...</div>
              </div>
            ) : skillProgress && stats ? (
              <SkillDetailModal
                skill={selectedSkill}
                skillData={stats.skills?.[selectedSkill] as SkillData | undefined}
                skillProgress={skillProgress}
                skillIcon={SKILL_ICONS[selectedSkill]}
                onClose={closeSkillModal}
              />
            ) : (
              <div className="p-8">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-2xl font-bold">
                    {selectedSkill.charAt(0).toUpperCase() + selectedSkill.slice(1)}
                  </h2>
                  <button
                    onClick={closeSkillModal}
                    className="text-gray-500 hover:text-gray-700 text-2xl"
                  >
                    ×
                  </button>
                </div>
                <div className="text-red-600">Failed to load skill progress data.</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Most Progressed Skills Component
interface MostProgressedSkillsProps {
  title: string;
  progress: ProgressAnalysisResponse | null;
  skillIcons: Record<string, string>;
}

const MostProgressedSkills: React.FC<MostProgressedSkillsProps> = ({
  title,
  progress,
  skillIcons,
}) => {
  if (!progress) {
    return (
      <div className="card">
        <h3 className="text-sm font-medium text-gray-500 mb-2">{title}</h3>
        <p className="text-sm text-gray-400">No data available</p>
      </div>
    );
  }

  // Get top 5 skills by experience gained
  const topSkills = Object.entries(progress.progress.experience_gained)
    .map(([skill, exp]) => ({
      skill,
      experience: exp,
      levels: progress.progress.levels_gained[skill] || 0,
    }))
    .filter((item) => item.experience > 0)
    .sort((a, b) => b.experience - a.experience)
    .slice(0, 5);

  if (topSkills.length === 0) {
    return (
      <div className="card">
        <h3 className="text-sm font-medium text-gray-500 mb-2">{title}</h3>
        <p className="text-sm text-gray-400">No progress recorded</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3 className="text-sm font-medium text-gray-500 mb-3">{title}</h3>
      <div className="space-y-2">
        {topSkills.map(({ skill, experience, levels }) => {
          const skillName = skill.charAt(0).toUpperCase() + skill.slice(1);
          const iconUrl = skillIcons[skill];
          return (
            <div
              key={skill}
              className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 transition-colors"
            >
              {iconUrl && iconUrl !== '⚓' ? (
                <img
                  src={iconUrl}
                  alt={skillName}
                  className="w-6 h-6 flex-shrink-0"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                  }}
                />
              ) : (
                <span className="w-6 h-6 flex items-center justify-center text-sm">{iconUrl || '❓'}</span>
              )}
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 truncate">{skillName}</div>
                <div className="text-xs text-gray-500">
                  {experience.toLocaleString()} XP
                  {levels > 0 && ` • +${levels} level${levels !== 1 ? 's' : ''}`}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Skill Detail Modal Component
interface SkillDetailModalProps {
  skill: string;
  skillData: SkillData | undefined;
  skillProgress: SkillProgressResponse;
  skillIcon: string | undefined;
  onClose: () => void;
}

const SkillDetailModal: React.FC<SkillDetailModalProps> = ({
  skill,
  skillData,
  skillProgress,
  skillIcon,
  onClose,
}) => {
  const currentLevel = skillData?.level ?? 0;
  const currentExp = skillData?.experience ?? 0;
  const maxLevel = skill === 'sailing' ? 1 : 99;
  const isMaxLevel = currentLevel >= maxLevel;

  // Calculate time estimates
  const dailyRate = skillProgress.progress.daily_experience_rate;
  const expToNextLevel = isMaxLevel ? 0 : getExpToNextLevel(currentLevel, currentExp);
  const expToMax = isMaxLevel ? 0 : getExpToMax(currentLevel, currentExp);

  const timeToNextLevel = dailyRate > 0 && !isMaxLevel
    ? formatDuration(expToNextLevel / dailyRate)
    : isMaxLevel ? 'Max level reached!' : 'Insufficient data';

  const timeToMax = dailyRate > 0 && !isMaxLevel
    ? formatDuration(expToMax / dailyRate)
    : isMaxLevel ? 'Max level reached!' : 'Insufficient data';

  // Prepare timeline data for chart
  const timelineData = skillProgress.timeline.map((entry) => ({
    date: format(new Date(entry.date), 'MMM d'),
    level: entry.level ?? 0,
    experience: entry.experience ?? 0,
  }));

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div className="flex items-center gap-4">
          {skillIcon && skillIcon !== '⚓' ? (
            <img src={skillIcon} alt={skill} className="w-12 h-12" />
          ) : (
            <span className="text-4xl">{skillIcon || '❓'}</span>
          )}
          <div>
            <h2 className="text-3xl font-bold">
              {skill.charAt(0).toUpperCase() + skill.slice(1)}
            </h2>
            <p className="text-gray-500">
              {skillProgress.period_days} days of history • {skillProgress.total_records} records
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700 text-3xl leading-none"
        >
          ×
        </button>
      </div>

      {/* Current Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="card">
          <h3 className="text-sm font-medium text-gray-500 mb-1">Current Level</h3>
          <p className="text-2xl font-bold text-primary-600">
            {currentLevel}/{maxLevel}
          </p>
        </div>
        <div className="card">
          <h3 className="text-sm font-medium text-gray-500 mb-1">Experience</h3>
          <p className="text-2xl font-bold text-primary-600">
            {currentExp.toLocaleString()}
          </p>
        </div>
        <div className="card">
          <h3 className="text-sm font-medium text-gray-500 mb-1">Daily XP Rate</h3>
          <p className="text-2xl font-bold text-primary-600">
            {dailyRate > 0 ? Math.round(dailyRate).toLocaleString() : 'N/A'}
          </p>
        </div>
        <div className="card">
          <h3 className="text-sm font-medium text-gray-500 mb-1">Levels Gained</h3>
          <p className="text-2xl font-bold text-primary-600">
            {skillProgress.progress.levels_gained}
          </p>
        </div>
      </div>

      {/* Time Estimates */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="card">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Time to Next Level</h3>
          <div className="space-y-1">
            <p className="text-xl font-bold text-primary-600">{timeToNextLevel}</p>
            {!isMaxLevel && dailyRate > 0 && (
              <p className="text-sm text-gray-500">
                {expToNextLevel.toLocaleString()} XP needed
              </p>
            )}
          </div>
        </div>
        <div className="card">
          <h3 className="text-sm font-medium text-gray-500 mb-2">Time to Max Level</h3>
          <div className="space-y-1">
            <p className="text-xl font-bold text-primary-600">{timeToMax}</p>
            {!isMaxLevel && dailyRate > 0 && (
              <p className="text-sm text-gray-500">
                {expToMax.toLocaleString()} XP needed
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Progress Summary */}
      <div className="card mb-6">
        <h3 className="text-lg font-bold mb-4">Progress Summary ({skillProgress.period_days} days)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500 mb-1">Experience Gained</p>
            <p className="text-2xl font-bold">
              {skillProgress.progress.experience_gained.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 mb-1">Average Daily XP</p>
            <p className="text-2xl font-bold">
              {Math.round(skillProgress.progress.daily_experience_rate).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* History Chart */}
      {timelineData.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-bold mb-4">Experience History</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timelineData} margin={{ top: 10, right: 60, left: 80, bottom: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  angle={-45}
                  textAnchor="end"
                  height={120}
                  tick={{ fontSize: 14, fill: '#1f2937', fontWeight: 500 }}
                  interval="preserveStartEnd"
                  stroke="#6b7280"
                />
                <YAxis
                  yAxisId="exp"
                  tick={{ fontSize: 14, fill: '#1f2937', fontWeight: 500 }}
                  stroke="#6b7280"
                  label={{
                    value: 'Experience',
                    angle: -90,
                    position: 'insideLeft',
                    style: { textAnchor: 'middle', fill: '#1f2937', fontSize: 16, fontWeight: 600 }
                  }}
                  tickFormatter={(value) => {
                    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
                    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
                    return value.toString();
                  }}
                />
                <YAxis
                  yAxisId="level"
                  orientation="right"
                  tick={{ fontSize: 14, fill: '#059669', fontWeight: 600 }}
                  stroke="#059669"
                  label={{
                    value: 'Level',
                    angle: 90,
                    position: 'insideRight',
                    style: { textAnchor: 'middle', fill: '#059669', fontSize: 16, fontWeight: 600 }
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '2px solid #e5e7eb',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: 500,
                    padding: '12px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                  }}
                  labelStyle={{
                    marginBottom: '8px',
                    fontSize: '15px',
                    fontWeight: 600,
                    color: '#1f2937'
                  }}
                  formatter={(value: number, name: string) => {
                    if (name === 'experience') {
                      return [value.toLocaleString(), 'Experience'];
                    }
                    return [value, 'Level'];
                  }}
                />
                <Legend
                  wrapperStyle={{ paddingTop: '20px', fontSize: '14px', fontWeight: 500 }}
                  iconType="line"
                />
                <Line
                  type="monotone"
                  dataKey="experience"
                  stroke="#0ea5e9"
                  strokeWidth={2.5}
                  name="Experience"
                  yAxisId="exp"
                  dot={{ r: 4, fill: '#0ea5e9' }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  type="monotone"
                  dataKey="level"
                  stroke="#10b981"
                  strokeWidth={2.5}
                  name="Level"
                  yAxisId="level"
                  dot={{ r: 4, fill: '#10b981' }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

