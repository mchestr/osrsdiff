import { format } from 'date-fns';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api/apiClient';
import type { BossProgressResponse } from '../api/models/BossProgressResponse';
import type { PlayerMetadataResponse } from '../api/models/PlayerMetadataResponse';
import type { PlayerStatsResponse } from '../api/models/PlayerStatsResponse';
import type { ProgressAnalysisResponse } from '../api/models/ProgressAnalysisResponse';
import type { SkillProgressResponse } from '../api/models/SkillProgressResponse';
import { OverallXPGraph } from '../components/OverallXPGraph';
import { SkillsGrid } from '../components/SkillsGrid';
import { useAuth } from '../contexts/AuthContext';

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
import sailingIcon from '../assets/images/skill-icons/sailing-icon.png';
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
  sailing: sailingIcon,
};

// Type definitions for skill and boss data
interface SkillData {
  level?: number;
  experience?: number;
  rank?: number;
}

interface BossData {
  kc?: number | null;
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
  const { isAuthenticated } = useAuth();
  const [stats, setStats] = useState<PlayerStatsResponse | null>(null);
  const [progressDay, setProgressDay] = useState<ProgressAnalysisResponse | null>(null);
  const [progressWeek, setProgressWeek] = useState<ProgressAnalysisResponse | null>(null);
  const [progressMonth, setProgressMonth] = useState<ProgressAnalysisResponse | null>(null);
  const [metadata, setMetadata] = useState<PlayerMetadataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [skillProgress, setSkillProgress] = useState<SkillProgressResponse | null>(null);
  const [skillProgressLoading, setSkillProgressLoading] = useState(false);
  const [selectedBoss, setSelectedBoss] = useState<string | null>(null);
  const [bossProgress, setBossProgress] = useState<BossProgressResponse | null>(null);
  const [bossProgressLoading, setBossProgressLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!username) return;

      try {
        setLoading(true);
        const [statsRes, progressDayRes, progressWeekRes, progressMonthRes, metadataRes] = await Promise.all([
          api.StatisticsService.getPlayerStatsApiV1PlayersUsernameStatsGet(username),
          api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 1).catch(() => null),
          api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 7).catch(() => null),
          api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 30).catch(() => null),
          api.PlayersService.getPlayerMetadataApiV1PlayersUsernameMetadataGet(username).catch(() => null),
        ]);

        setStats(statsRes);
        setProgressDay(progressDayRes);
        setProgressWeek(progressWeekRes);
        setProgressMonth(progressMonthRes);
        setMetadata(metadataRes);
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

  const handleTriggerFetch = async () => {
    if (!username) return;

    setFetching(true);
    try {
      await api.PlayersService.triggerManualFetchApiV1PlayersUsernameFetchPost(username);
      alert('Fetch task enqueued successfully. Refreshing data...');
      // Refresh data after a short delay
      setTimeout(async () => {
        try {
          const [statsRes, progressDayRes, progressWeekRes, progressMonthRes, metadataRes] = await Promise.all([
            api.StatisticsService.getPlayerStatsApiV1PlayersUsernameStatsGet(username),
            api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 1).catch(() => null),
            api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 7).catch(() => null),
            api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 30).catch(() => null),
            api.PlayersService.getPlayerMetadataApiV1PlayersUsernameMetadataGet(username).catch(() => null),
          ]);

          setStats(statsRes);
          setProgressDay(progressDayRes);
          setProgressWeek(progressWeekRes);
          setProgressMonth(progressMonthRes);
          setMetadata(metadataRes);
        } catch (err) {
          console.error('Failed to refresh data:', err);
        }
      }, 2000);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to trigger fetch';
      const errorDetail = (error as { body?: { detail?: string } })?.body?.detail;
      alert(errorDetail || errorMessage);
    } finally {
      setFetching(false);
    }
  };

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

  const handleBossClick = async (bossName: string) => {
    if (!username) return;

    setSelectedBoss(bossName);
    setBossProgressLoading(true);

    try {
      const bossData = await api.HistoryService.getBossProgressApiV1PlayersUsernameHistoryBossesBossGet(
        username,
        bossName,
        90 // Get 90 days of history
      );
      setBossProgress(bossData);
    } catch (err: unknown) {
      console.error('Failed to load boss progress:', err);
      setBossProgress(null);
    } finally {
      setBossProgressLoading(false);
    }
  };

  const closeBossModal = () => {
    setSelectedBoss(null);
    setBossProgress(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="osrs-text text-xl">Loading...</div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="osrs-card">
        <div className="osrs-text" style={{ color: '#d32f2f' }}>{error || 'Player not found'}</div>
      </div>
    );
  }

  const bossNames = Object.keys(stats.bosses || {});

  // Get skills in OSRS order, always including all skills (even if data is missing)
  const orderedSkills = OSRS_SKILL_ORDER
    .map((skillName) => {
      const skillData = stats.skills?.[skillName] as SkillData | undefined;
      // Always include the skill, even if data is missing (defaults to level 1, experience 0)
      return {
        name: skillName,
        displayName: skillName.charAt(0).toUpperCase() + skillName.slice(1),
        level: skillData?.level ?? 1,
        experience: skillData?.experience ?? 0,
        maxLevel: 99, // All OSRS skills have max level 99
      };
    });

  // Prepare boss data for grid display
  const orderedBosses = bossNames
    .map((name) => {
      const bossData = stats.bosses?.[name] as BossData | undefined;
      if (!bossData || typeof bossData !== 'object') return null;
      const kills = bossData.kc ?? 0;
      return {
        name,
        displayName: name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
        kills: typeof kills === 'number' && kills !== null ? kills : 0,
        rank: bossData.rank ?? null,
      };
    })
    .filter((boss): boss is { name: string; displayName: string; kills: number; rank: number | null } => boss !== null && boss.kills > 0)
    .sort((a, b) => b.kills - a.kills);

  return (
    <div className="space-y-1">
      {/* Compact Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-1.5 mb-1">
        <h1 className="osrs-card-title text-xl sm:text-2xl" style={{ marginBottom: 0 }}>
          {stats.username}
        </h1>
        <div className="flex flex-wrap items-center gap-1.5">
          {stats.fetched_at && (
            <p className="osrs-text-secondary text-xs">
              {format(new Date(stats.fetched_at), 'MMM d, HH:mm')}
            </p>
          )}
          <a
            href={`https://secure.runescape.com/m=hiscore_oldschool/hiscorepersonal.ws?user1=${encodeURIComponent(stats.username)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="osrs-btn text-xs px-2 py-1"
            title="View on official OSRS hiscore"
          >
            OSRS
          </a>
          {isAuthenticated && (
            <button
              onClick={handleTriggerFetch}
              disabled={fetching}
              className="osrs-btn text-xs px-2 py-1"
            >
              {fetching ? '...' : 'Fetch'}
            </button>
          )}
        </div>
      </div>

      {/* Overall XP Graph - Full Width */}
      {username && (
        <div className="mb-1.5">
          <OverallXPGraph username={username} />
        </div>
      )}

      {/* Main Stats Grid - Compact */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-1.5">
        {/* Skills Grid */}
        <div className="lg:col-span-4">
          <SkillsGrid
            skills={orderedSkills}
            skillIcons={SKILL_ICONS}
            totalLevel={stats.overall?.level ?? 0}
            onSkillClick={handleSkillClick}
          />
        </div>

        {/* Top 10 Skills Progress */}
        <div className="lg:col-span-4">
          <TopProgressHighlights
            progressWeek={progressWeek}
            skillIcons={SKILL_ICONS}
          />
        </div>

        {/* Top 10 Bosses Progress */}
        <div className="lg:col-span-4">
          <TopBossProgressHighlights
            progressWeek={progressWeek}
            orderedBosses={orderedBosses}
            onBossClick={handleBossClick}
          />
        </div>
      </div>

      {/* Skills Summary Table */}
      <SkillsSummaryTable
        progressDay={progressDay}
        progressWeek={progressWeek}
        progressMonth={progressMonth}
        skillIcons={SKILL_ICONS}
        orderedSkills={orderedSkills}
        onSkillClick={handleSkillClick}
      />

      {/* Boss Progress Summary */}
      {orderedBosses.length > 0 && (
        <BossProgressSummary
          progressDay={progressDay}
          progressWeek={progressWeek}
          progressMonth={progressMonth}
          orderedBosses={orderedBosses}
          onBossClick={handleBossClick}
        />
      )}


      {/* Skill Detail Modal */}
      {selectedSkill && (
        <div
          className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4"
          onClick={closeSkillModal}
        >
          <div
            className="osrs-card max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {skillProgressLoading ? (
              <div className="p-8 text-center">
                <div className="osrs-text text-xl">Loading skill details...</div>
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
                  <h2 className="osrs-card-title text-2xl">
                    {selectedSkill.charAt(0).toUpperCase() + selectedSkill.slice(1)}
                  </h2>
                  <button
                    onClick={closeSkillModal}
                    className="osrs-text hover:opacity-70 text-3xl leading-none"
                  >
                    ×
                  </button>
                </div>
                <div className="osrs-text">Failed to load skill progress data.</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Boss Detail Modal */}
      {selectedBoss && (
        <div
          className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4"
          onClick={closeBossModal}
        >
          <div
            className="osrs-card max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {bossProgressLoading ? (
              <div className="p-8 text-center">
                <div className="osrs-text text-xl">Loading boss details...</div>
              </div>
            ) : bossProgress && stats ? (
              <BossDetailModal
                boss={selectedBoss}
                bossData={stats.bosses?.[selectedBoss] as BossData | undefined}
                bossProgress={bossProgress}
                onClose={closeBossModal}
              />
            ) : (
              <div className="p-8">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="osrs-card-title text-2xl">
                    {selectedBoss.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </h2>
                  <button
                    onClick={closeBossModal}
                    className="osrs-text hover:opacity-70 text-3xl leading-none"
                  >
                    ×
                  </button>
                </div>
                <div className="osrs-text">Failed to load boss progress data.</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Player Metadata - Collapsible */}
      {metadata && (
        <div className="osrs-card">
          <button
            onClick={() => setMetadataExpanded(!metadataExpanded)}
            className="w-full flex justify-between items-center text-left"
          >
            <h2 className="osrs-card-title text-sm">Player Information</h2>
            <span className="osrs-text text-lg">
              {metadataExpanded ? '−' : '+'}
            </span>
          </button>
          {metadataExpanded && (
            <div className="mt-3 pt-3 border-t border-8b7355" style={{ borderColor: '#8b7355' }}>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
                <div>
                  <h3 className="osrs-stat-label mb-1">Status</h3>
                  <p>
                    <span
                      className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold ${
                        metadata.is_active
                          ? 'osrs-text'
                          : 'osrs-text-secondary'
                      }`}
                      style={{
                        backgroundColor: metadata.is_active ? 'rgba(255, 215, 0, 0.2)' : 'rgba(139, 115, 85, 0.2)',
                        border: `1px solid ${metadata.is_active ? '#ffd700' : '#8b7355'}`
                      }}
                    >
                      {metadata.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </p>
                </div>
                <div>
                  <h3 className="osrs-stat-label mb-1">Fetch Interval</h3>
                  <p className="osrs-text">
                    {metadata.fetch_interval_minutes} minutes
                    {metadata.fetch_interval_minutes >= 60 && (
                      <span className="osrs-text-secondary ml-1">
                        ({Math.round(metadata.fetch_interval_minutes / 60 * 10) / 10} hours)
                      </span>
                    )}
                  </p>
                </div>
                <div>
                  <h3 className="osrs-stat-label mb-1">Total Records</h3>
                  <p className="osrs-text">
                    {metadata.total_records.toLocaleString()}
                  </p>
                </div>
                <div>
                  <h3 className="osrs-stat-label mb-1">Created</h3>
                  <p className="osrs-text">
                    {format(new Date(metadata.created_at), 'MMM d, yyyy')}
                  </p>
                </div>
                <div>
                  <h3 className="osrs-stat-label mb-1">Last Fetched</h3>
                  <p className="osrs-text">
                    {metadata.last_fetched
                      ? format(new Date(metadata.last_fetched), 'MMM d, yyyy HH:mm')
                      : 'Never'}
                  </p>
                </div>
                {metadata.avg_fetch_frequency_hours && (
                  <div>
                    <h3 className="osrs-stat-label mb-1">Avg Fetch Frequency</h3>
                    <p className="osrs-text">
                      {Math.round(metadata.avg_fetch_frequency_hours * 10) / 10} hours
                    </p>
                  </div>
                )}
                {metadata.first_record && (
                  <div>
                    <h3 className="osrs-stat-label mb-1">First Record</h3>
                    <p className="osrs-text">
                      {format(new Date(metadata.first_record), 'MMM d, yyyy')}
                    </p>
                  </div>
                )}
                {metadata.latest_record && (
                  <div>
                    <h3 className="osrs-stat-label mb-1">Latest Record</h3>
                    <p className="osrs-text">
                      {format(new Date(metadata.latest_record), 'MMM d, yyyy HH:mm')}
                    </p>
                  </div>
                )}
                <div>
                  <h3 className="osrs-stat-label mb-1">Records (24h)</h3>
                  <p className="osrs-text">
                    {metadata.records_last_24h}
                  </p>
                </div>
                <div>
                  <h3 className="osrs-stat-label mb-1">Records (7d)</h3>
                  <p className="osrs-text">
                    {metadata.records_last_7d}
                  </p>
                </div>
                {metadata.schedule_id && (
                  <div>
                    <h3 className="osrs-stat-label mb-1">Schedule ID</h3>
                    <p className="osrs-text-secondary text-xs font-mono break-all">
                      {metadata.schedule_id}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};


// Top Progress Highlights Component - Top 10 skills from last 7 days
interface TopProgressHighlightsProps {
  progressWeek: ProgressAnalysisResponse | null;
  skillIcons: Record<string, string>;
}

const TopProgressHighlights: React.FC<TopProgressHighlightsProps> = ({
  progressWeek,
  skillIcons,
}) => {
  const getTopSkills = (progress: ProgressAnalysisResponse | null, count: number = 10) => {
    if (!progress) return [];
    return Object.entries(progress.progress.experience_gained)
      .filter(([skill]) => skill !== 'overall')
      .map(([skill, exp]) => ({
        skill,
        experience: exp,
        levels: progress.progress.levels_gained[skill] || 0,
      }))
      .filter((item) => item.experience > 0)
      .sort((a, b) => b.experience - a.experience)
      .slice(0, count);
  };

  const topSkills = getTopSkills(progressWeek, 10);

  return (
    <div className="osrs-card h-full" style={{ padding: '12px' }}>
      <h3 className="osrs-card-title text-sm mb-1.5" style={{ marginBottom: '8px' }}>Top 10 Skills (7d)</h3>
      {topSkills.length > 0 ? (
        <div className="space-y-1.5 max-h-[400px] overflow-y-auto">
          {topSkills.map((skillData, index) => (
            <div key={skillData.skill} className="flex items-center gap-2">
              <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center osrs-text text-xs font-bold">
                #{index + 1}
              </div>
              {skillIcons[skillData.skill] && skillIcons[skillData.skill] !== '⚓' ? (
                <img
                  src={skillIcons[skillData.skill]}
                  alt={skillData.skill}
                  className="w-5 h-5 flex-shrink-0"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                  }}
                />
              ) : (
                <span className="w-5 h-5 flex items-center justify-center text-xs">{skillIcons[skillData.skill] || '❓'}</span>
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="osrs-text text-xs font-semibold capitalize truncate">{skillData.skill}</span>
                  <span className="osrs-text text-xs font-medium whitespace-nowrap">
                    {skillData.experience.toLocaleString()}
                  </span>
                </div>
                {skillData.levels > 0 && (
                  <div className="osrs-text-secondary text-xs">
                    +{skillData.levels} level{skillData.levels !== 1 ? 's' : ''}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="osrs-text-secondary text-xs text-center py-4">No progress</div>
      )}
    </div>
  );
};

// Top Boss Progress Highlights Component - Top 10 bosses from last 7 days
interface TopBossProgressHighlightsProps {
  progressWeek: ProgressAnalysisResponse | null;
  orderedBosses: Array<{ name: string; displayName: string; kills: number; rank: number | null }>;
  onBossClick: (bossName: string) => void;
}

const TopBossProgressHighlights: React.FC<TopBossProgressHighlightsProps> = ({
  progressWeek,
  orderedBosses,
  onBossClick,
}) => {
  const getTopBosses = (progress: ProgressAnalysisResponse | null, count: number = 10) => {
    if (!progress) return [];
    return Object.entries(progress.progress.boss_kills_gained || {})
      .map(([boss, kills]) => ({
        boss,
        kills: typeof kills === 'number' ? kills : 0,
      }))
      .filter((item) => item.kills > 0)
      .sort((a, b) => b.kills - a.kills)
      .slice(0, count)
      .map((item) => {
        const bossData = orderedBosses.find((b) => b.name === item.boss);
        return {
          ...item,
          displayName: bossData?.displayName || item.boss.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
        };
      });
  };

  const topBosses = getTopBosses(progressWeek, 10);

  return (
    <div className="osrs-card h-full" style={{ padding: '12px' }}>
      <h3 className="osrs-card-title text-sm mb-1.5" style={{ marginBottom: '8px' }}>Top 10 Bosses (7d)</h3>
      {topBosses.length > 0 ? (
        <div className="space-y-1.5 max-h-[400px] overflow-y-auto">
          {topBosses.map((bossData, index) => (
            <div
              key={bossData.boss}
              className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
              onClick={() => onBossClick(bossData.boss)}
              title={`Click to view ${bossData.displayName} details`}
            >
              <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center osrs-text text-xs font-bold">
                #{index + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="osrs-text text-xs font-semibold capitalize truncate">{bossData.displayName}</span>
                  <span className="font-semibold text-green-400 text-xs whitespace-nowrap">
                    +{bossData.kills.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="osrs-text-secondary text-xs text-center py-4">No progress</div>
      )}
    </div>
  );
};

// Boss Progress Summary Component
interface BossProgressSummaryProps {
  progressDay: ProgressAnalysisResponse | null;
  progressWeek: ProgressAnalysisResponse | null;
  progressMonth: ProgressAnalysisResponse | null;
  orderedBosses: Array<{ name: string; displayName: string; kills: number; rank: number | null }>;
  onBossClick: (bossName: string) => void;
}

const BossProgressSummary: React.FC<BossProgressSummaryProps> = ({
  progressDay,
  progressWeek,
  progressMonth,
  orderedBosses,
  onBossClick,
}) => {
  const [selectedPeriod, setSelectedPeriod] = useState<number>(7);

  const getProgressForPeriod = (period: number): ProgressAnalysisResponse | null => {
    switch (period) {
      case 1:
        return progressDay;
      case 7:
        return progressWeek;
      case 30:
        return progressMonth;
      default:
        return progressWeek;
    }
  };

  const currentProgress = getProgressForPeriod(selectedPeriod);

  const getBossProgress = (bossName: string) => {
    if (!currentProgress) {
      return { kills: 0 };
    }
    return {
      kills: currentProgress.progress.boss_kills_gained?.[bossName] || 0,
    };
  };

  const getPeriodLabel = (period: number) => {
    switch (period) {
      case 1:
        return '1d';
      case 7:
        return '7d';
      case 30:
        return '30d';
      default:
        return '7d';
    }
  };

  return (
    <div className="osrs-card">
      <div className="flex justify-between items-center mb-4">
        <h2 className="osrs-card-title">Boss Progress Summary</h2>
        <select
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(Number(e.target.value))}
          className="osrs-btn px-3 py-1.5 text-sm"
        >
          <option value={1}>Last 1 Day</option>
          <option value={7}>Last 7 Days</option>
          <option value={30}>Last 30 Days</option>
        </select>
      </div>

      {currentProgress ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2">
          {orderedBosses.map((boss) => {
            const progress = getBossProgress(boss.name);
            return (
              <div
                key={boss.name}
                className="cursor-pointer hover:opacity-80 transition-opacity"
                style={{
                  backgroundColor: progress.kills > 0 ? 'rgba(255, 215, 0, 0.05)' : '#3a3a3a',
                  border: '2px solid #8b7355',
                  borderRadius: '2px',
                  minHeight: '48px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '8px 4px',
                  gap: '4px',
                }}
                onClick={() => onBossClick(boss.name)}
                title={`Click to view ${boss.displayName} details`}
              >
                <div className="osrs-text text-xs font-semibold text-center w-full px-1 leading-tight truncate">
                  {boss.displayName}
                </div>
                <div
                  className="font-bold text-base"
                  style={{
                    color: '#ffd700',
                    fontFamily: 'Courier New, Courier, monospace',
                    textShadow: '2px 2px 0px rgba(0, 0, 0, 1), -1px -1px 0px rgba(0, 0, 0, 1), 1px -1px 0px rgba(0, 0, 0, 1), -1px 1px 0px rgba(0, 0, 0, 1)',
                    textAlign: 'center',
                    margin: '0',
                  }}
                >
                  {boss.kills.toLocaleString()}
                </div>
                {progress.kills > 0 ? (
                  <div className="font-semibold text-green-400 text-xs text-center w-full">
                    +{progress.kills.toLocaleString()} ({getPeriodLabel(selectedPeriod)})
                  </div>
                ) : (
                  <div className="osrs-text-secondary text-xs text-center w-full">
                    0 ({getPeriodLabel(selectedPeriod)})
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="osrs-text-secondary text-center py-8">
          No progress data available for the selected period
        </div>
      )}
    </div>
  );
};

// Skills Summary Table Component
interface SkillsSummaryTableProps {
  progressDay: ProgressAnalysisResponse | null;
  progressWeek: ProgressAnalysisResponse | null;
  progressMonth: ProgressAnalysisResponse | null;
  skillIcons: Record<string, string>;
  orderedSkills: Array<{ name: string; displayName: string; level: number; experience: number; maxLevel: number }>;
  onSkillClick: (skillName: string) => void;
}

const SkillsSummaryTable: React.FC<SkillsSummaryTableProps> = ({
  progressDay,
  progressWeek,
  progressMonth,
  skillIcons,
  orderedSkills,
  onSkillClick,
}) => {
  const [selectedPeriod, setSelectedPeriod] = useState<number>(7);

  const getProgressForPeriod = (period: number): ProgressAnalysisResponse | null => {
    switch (period) {
      case 1:
        return progressDay;
      case 7:
        return progressWeek;
      case 30:
        return progressMonth;
      default:
        return progressWeek;
    }
  };

  const currentProgress = getProgressForPeriod(selectedPeriod);

  const getSkillProgress = (skillName: string) => {
    if (!currentProgress) {
      return { experience: 0, levels: 0 };
    }
    return {
      experience: currentProgress.progress.experience_gained[skillName] || 0,
      levels: currentProgress.progress.levels_gained[skillName] || 0,
    };
  };

  return (
    <div className="osrs-card">
      <div className="flex justify-between items-center mb-4">
        <h2 className="osrs-card-title">Skills Progress Summary</h2>
        <select
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(Number(e.target.value))}
          className="osrs-btn px-3 py-1.5 text-sm"
        >
          <option value={1}>Last 1 Day</option>
          <option value={7}>Last 7 Days</option>
          <option value={30}>Last 30 Days</option>
        </select>
      </div>

      {currentProgress ? (
        <div className="overflow-x-auto">
          <table className="w-full" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #8b7355' }}>
                <th className="osrs-text text-left py-2 px-3 font-semibold" style={{ minWidth: '200px' }}>Skill</th>
                <th className="osrs-text text-right py-2 px-3 font-semibold">Current Level</th>
                <th className="osrs-text text-right py-2 px-3 font-semibold">Levels Gained</th>
                <th className="osrs-text text-right py-2 px-3 font-semibold">Experience Gained</th>
              </tr>
            </thead>
            <tbody>
              {orderedSkills.map((skill) => {
                const progress = getSkillProgress(skill.name);
                const iconUrl = skillIcons[skill.name];
                return (
                  <tr
                    key={skill.name}
                    className="hover:bg-opacity-10"
                    style={{ borderBottom: '1px solid #8b7355', backgroundColor: progress.experience > 0 ? 'rgba(255, 215, 0, 0.05)' : 'transparent' }}
                  >
                    <td className="py-2 px-3">
                      <div
                        className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
                        onClick={() => onSkillClick(skill.name)}
                        title={`Click to view ${skill.displayName} details`}
                      >
                        {iconUrl && iconUrl !== '⚓' ? (
                          <img
                            src={iconUrl}
                            alt={skill.displayName}
                            className="w-5 h-5 flex-shrink-0"
                            onError={(e) => {
                              const target = e.target as HTMLImageElement;
                              target.style.display = 'none';
                            }}
                          />
                        ) : (
                          <span className="w-5 h-5 flex items-center justify-center text-xs">{iconUrl || '❓'}</span>
                        )}
                        <span className="osrs-text font-medium">{skill.displayName}</span>
                      </div>
                    </td>
                    <td className="osrs-text text-right py-2 px-3">
                      <span className="font-semibold">{skill.level}</span>
                    </td>
                    <td className="osrs-text text-right py-2 px-3">
                      {progress.levels > 0 ? (
                        <span className="font-semibold text-green-400">+{progress.levels}</span>
                      ) : (
                        <span className="osrs-text-secondary">0</span>
                      )}
                    </td>
                    <td className="osrs-text text-right py-2 px-3">
                      {progress.experience > 0 ? (
                        <span className="font-semibold">{progress.experience.toLocaleString()}</span>
                      ) : (
                        <span className="osrs-text-secondary">0</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="osrs-text-secondary text-center py-8">
          No progress data available for the selected period
        </div>
      )}
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
  const currentLevel = skillData?.level ?? 1;
  const currentExp = skillData?.experience ?? 0;
  const maxLevel = 99; // All OSRS skills have max level 99
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

  // Calculate y-axis domain for experience based on first record to avoid flat line appearance
  const experienceValues = timelineData.map((d) => d.experience).filter((v) => v > 0);
  const minExperience = experienceValues.length > 0 ? Math.min(...experienceValues) : 0;
  const maxExperience = experienceValues.length > 0 ? Math.max(...experienceValues) : 0;
  const range = maxExperience - minExperience;
  // Add 5% padding below min and above max, but ensure min doesn't go below 0
  // If range is 0 or very small, use a minimum padding of 1% of the value
  const padding = range > 0 ? range * 0.05 : Math.max(minExperience * 0.01, 1000);
  const experienceYAxisDomain = [
    Math.max(0, minExperience - padding),
    maxExperience + padding,
  ];

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
            <h2 className="osrs-card-title text-3xl">
              {skill.charAt(0).toUpperCase() + skill.slice(1)}
            </h2>
            <p className="osrs-text-secondary">
              {skillProgress.period_days} days of history • {skillProgress.total_records} records
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="osrs-text hover:opacity-70 text-3xl leading-none"
        >
          ×
        </button>
      </div>

      {/* Current Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="osrs-card">
          <h3 className="osrs-stat-label mb-1">Current Level</h3>
          <p className="osrs-stat-value text-2xl">
            {currentLevel}/{maxLevel}
          </p>
        </div>
        <div className="osrs-card">
          <h3 className="osrs-stat-label mb-1">Experience</h3>
          <p className="osrs-stat-value text-2xl">
            {currentExp.toLocaleString()}
          </p>
        </div>
        <div className="osrs-card">
          <h3 className="osrs-stat-label mb-1">Daily XP Rate</h3>
          <p className="osrs-stat-value text-2xl">
            {dailyRate > 0 ? Math.round(dailyRate).toLocaleString() : 'N/A'}
          </p>
        </div>
        <div className="osrs-card">
          <h3 className="osrs-stat-label mb-1">Levels Gained</h3>
          <p className="osrs-stat-value text-2xl">
            {skillProgress.progress.levels_gained}
          </p>
        </div>
      </div>

      {/* Time Estimates */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="osrs-card">
          <h3 className="osrs-stat-label mb-2">Time to Next Level</h3>
          <div className="space-y-1">
            <p className="osrs-stat-value text-xl">{timeToNextLevel}</p>
            {!isMaxLevel && dailyRate > 0 && (
              <p className="osrs-text-secondary text-sm">
                {expToNextLevel.toLocaleString()} XP needed
              </p>
            )}
          </div>
        </div>
        <div className="osrs-card">
          <h3 className="osrs-stat-label mb-2">Time to Max Level</h3>
          <div className="space-y-1">
            <p className="osrs-stat-value text-xl">{timeToMax}</p>
            {!isMaxLevel && dailyRate > 0 && (
              <p className="osrs-text-secondary text-sm">
                {expToMax.toLocaleString()} XP needed
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Progress Summary */}
      <div className="osrs-card mb-6">
        <h3 className="osrs-card-title mb-4">Progress Summary ({skillProgress.period_days} days)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="osrs-stat-label mb-1">Experience Gained</p>
            <p className="osrs-stat-value text-2xl">
              {skillProgress.progress.experience_gained.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="osrs-stat-label mb-1">Average Daily XP</p>
            <p className="osrs-stat-value text-2xl">
              {Math.round(skillProgress.progress.daily_experience_rate).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* History Chart */}
      {timelineData.length > 0 && (
        <div className="osrs-card">
          <h3 className="osrs-card-title mb-4">Experience History</h3>
          <div className="h-80" style={{ backgroundColor: '#1d1611' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timelineData} margin={{ top: 20, right: 60, left: 100 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#8b7355" opacity={0.3} />
                <XAxis
                  dataKey="date"
                  angle={-45}
                  textAnchor="end"
                  height={100}
                  tick={{ fontSize: 14, fill: '#ffd700', fontWeight: 500 }}
                  interval="preserveStartEnd"
                  stroke="#8b7355"
                />
                <YAxis
                  yAxisId="exp"
                  domain={experienceYAxisDomain}
                  tick={{ fontSize: 14, fill: '#ffd700', fontWeight: 500 }}
                  stroke="#8b7355"
                  label={{
                    value: 'Experience',
                    angle: -90,
                    position: 'insideLeft',
                    offset: -10,
                    style: { textAnchor: 'middle', fill: '#ffd700', fontSize: 16, fontWeight: 600 }
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
                  tick={{ fontSize: 14, fill: '#ffd700', fontWeight: 600 }}
                  stroke="#8b7355"
                  label={{
                    value: 'Level',
                    angle: 90,
                    position: 'insideRight',
                    style: { textAnchor: 'middle', fill: '#ffd700', fontSize: 16, fontWeight: 600 }
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#2d2418',
                    border: '2px solid #8b7355',
                    borderRadius: '0',
                    fontSize: '14px',
                    fontWeight: 500,
                    padding: '12px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                    color: '#ffd700'
                  }}
                  labelStyle={{
                    marginBottom: '8px',
                    fontSize: '15px',
                    fontWeight: 600,
                    color: '#ffd700'
                  }}
                  formatter={(value: number, name: string) => {
                    if (name === 'experience') {
                      return [value.toLocaleString(), 'Experience'];
                    }
                    return [value, 'Level'];
                  }}
                />
                <Legend
                  wrapperStyle={{ paddingTop: '0px', marginTop: '0px', fontSize: '14px', fontWeight: 500, color: '#ffd700' }}
                  iconType="line"
                />
                <Line
                  type="monotone"
                  dataKey="experience"
                  stroke="#ffd700"
                  strokeWidth={2.5}
                  name="Experience"
                  yAxisId="exp"
                  dot={{ r: 4, fill: '#ffd700' }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  type="monotone"
                  dataKey="level"
                  stroke="#d4af37"
                  strokeWidth={2.5}
                  name="Level"
                  yAxisId="level"
                  dot={{ r: 4, fill: '#d4af37' }}
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

// Boss Detail Modal Component
interface BossDetailModalProps {
  boss: string;
  bossData: BossData | undefined;
  bossProgress: BossProgressResponse;
  onClose: () => void;
}

const BossDetailModal: React.FC<BossDetailModalProps> = ({
  boss,
  bossData,
  bossProgress,
  onClose,
}) => {
  const currentKills = bossData?.kc ?? 0;
  const dailyRate = bossProgress.progress.daily_kill_rate;

  // Prepare timeline data for chart
  const timelineData = bossProgress.timeline.map((entry) => ({
    date: format(new Date(entry.date), 'MMM d'),
    kc: entry.kc ?? 0,
  }));

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="osrs-card-title text-3xl">
            {boss.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
          </h2>
          <p className="osrs-text-secondary">
            {bossProgress.period_days} days of history • {bossProgress.total_records} records
          </p>
        </div>
        <button
          onClick={onClose}
          className="osrs-text hover:opacity-70 text-3xl leading-none"
        >
          ×
        </button>
      </div>

      {/* Current Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="osrs-card">
          <h3 className="osrs-stat-label mb-1">Current Kills</h3>
          <p className="osrs-stat-value text-2xl">
            {currentKills.toLocaleString()}
          </p>
        </div>
        <div className="osrs-card">
          <h3 className="osrs-stat-label mb-1">Daily Kill Rate</h3>
          <p className="osrs-stat-value text-2xl">
            {dailyRate > 0 ? Math.round(dailyRate).toLocaleString() : 'N/A'}
          </p>
        </div>
        <div className="osrs-card">
          <h3 className="osrs-stat-label mb-1">Kills Gained</h3>
          <p className="osrs-stat-value text-2xl">
            {bossProgress.progress.kills_gained.toLocaleString()}
          </p>
        </div>
        {bossData?.rank && (
          <div className="osrs-card">
            <h3 className="osrs-stat-label mb-1">Rank</h3>
            <p className="osrs-stat-value text-2xl">
              {bossData.rank.toLocaleString()}
            </p>
          </div>
        )}
      </div>

      {/* Progress Summary */}
      <div className="osrs-card mb-6">
        <h3 className="osrs-card-title mb-4">Progress Summary ({bossProgress.period_days} days)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="osrs-stat-label mb-1">Kills Gained</p>
            <p className="osrs-stat-value text-2xl">
              {bossProgress.progress.kills_gained.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="osrs-stat-label mb-1">Average Daily Kills</p>
            <p className="osrs-stat-value text-2xl">
              {Math.round(bossProgress.progress.daily_kill_rate).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* History Chart */}
      {timelineData.length > 0 && (
        <div className="osrs-card">
          <h3 className="osrs-card-title mb-4">Kill Count History</h3>
          <div className="h-80" style={{ backgroundColor: '#1d1611' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timelineData} margin={{ top: 20, right: 60, left: 100 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#8b7355" opacity={0.3} />
                <XAxis
                  dataKey="date"
                  angle={-45}
                  textAnchor="end"
                  height={100}
                  tick={{ fontSize: 14, fill: '#ffd700', fontWeight: 500 }}
                  interval="preserveStartEnd"
                  stroke="#8b7355"
                />
                <YAxis
                  tick={{ fontSize: 14, fill: '#ffd700', fontWeight: 500 }}
                  stroke="#8b7355"
                  label={{
                    value: 'Kill Count',
                    angle: -90,
                    position: 'insideLeft',
                    offset: -10,
                    style: { textAnchor: 'middle', fill: '#ffd700', fontSize: 16, fontWeight: 600 }
                  }}
                  tickFormatter={(value) => {
                    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
                    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
                    return value.toString();
                  }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#2d2418',
                    border: '2px solid #8b7355',
                    borderRadius: '0',
                    fontSize: '14px',
                    fontWeight: 500,
                    padding: '12px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                    color: '#ffd700'
                  }}
                  labelStyle={{
                    marginBottom: '8px',
                    fontSize: '15px',
                    fontWeight: 600,
                    color: '#ffd700'
                  }}
                  formatter={(value: number) => {
                    return [value.toLocaleString(), 'Kill Count'];
                  }}
                />
                <Legend
                  wrapperStyle={{ paddingTop: '0px', marginTop: '0px', fontSize: '14px', fontWeight: 500, color: '#ffd700' }}
                  iconType="line"
                />
                <Line
                  type="monotone"
                  dataKey="kc"
                  stroke="#ffd700"
                  strokeWidth={2.5}
                  name="Kill Count"
                  dot={{ r: 4, fill: '#ffd700' }}
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

