import { format } from 'date-fns';
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useParams } from 'react-router-dom';
import { api } from '../api/apiClient';
import type { BossProgressResponse } from '../api/models/BossProgressResponse';
import type { PlayerMetadataResponse } from '../api/models/PlayerMetadataResponse';
import type { PlayerStatsResponse } from '../api/models/PlayerStatsResponse';
import type { ProgressAnalysisResponse } from '../api/models/ProgressAnalysisResponse';
import type { SkillProgressResponse } from '../api/models/SkillProgressResponse';
import { ErrorDisplay } from '../components/ErrorDisplay';
import { GameModeBadge } from '../components/GameModeBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { OverallXPGraph } from '../components/OverallXPGraph';
import {
  BossDetailModal,
  BossProgressTable,
  PlayerMetadata,
  ProgressSummary,
  SkillDetailModal,
  SkillsProgressTable,
  TopBossesList,
  TopSkillsChart,
  TopSkillsList,
} from '../components/playerStats';
import { SkillsGrid } from '../components/SkillsGrid';
import { StatsCard } from '../components/StatsCard';
import { useAuth } from '../contexts/AuthContext';
import { useNotificationContext } from '../contexts/NotificationContext';
import type { BossData, OrderedBoss, OrderedSkill, PlayerSummary, SkillData } from '../types/player';
import { extractErrorMessage } from '../utils/errorHandler';
import { formatNumberLocale } from '../utils/formatters';
import { OSRS_SKILL_ORDER } from '../utils/osrs';
import { SKILL_ICONS } from '../utils/skillIcons';

export const PlayerStats: React.FC = () => {
  const { username } = useParams<{ username: string }>();
  const { isAuthenticated, isAdmin } = useAuth();
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
  const [summary, setSummary] = useState<PlayerSummary | null>(null);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [recalculatingGameMode, setRecalculatingGameMode] = useState(false);
  const { showNotification } = useNotificationContext();
  const [polling, setPolling] = useState(false);
  const pollAttemptsRef = useRef(0);
  const MAX_POLL_ATTEMPTS = 15;
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [isActionsMenuOpen, setIsActionsMenuOpen] = useState(false);
  const [actionsMenuPosition, setActionsMenuPosition] = useState<{ top: number; right: number } | null>(null);
  const actionsMenuButtonRef = useRef<HTMLButtonElement>(null);
  const actionsMenuDropdownRef = useRef<HTMLDivElement>(null);

  const fetchData = useCallback(async (isPolling = false) => {
    if (!username) return;

    try {
      if (!isPolling) {
        setLoading(true);
      }
      const [statsRes, progressDayRes, progressWeekRes, progressMonthRes, metadataRes, summaryRes] = await Promise.all([
        api.StatisticsService.getPlayerStatsApiV1PlayersUsernameStatsGet(username),
        api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 1).catch(() => null),
        api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 7).catch(() => null),
        api.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, null, null, 30).catch(() => null),
        api.PlayersService.getPlayerMetadataApiV1PlayersUsernameMetadataGet(username).catch(() => null),
        api.PlayersService.getPlayerSummaryApiV1PlayersUsernameSummaryGet(username).catch(() => null),
      ]);

      setStats(statsRes);
      setProgressDay(progressDayRes);
      setProgressWeek(progressWeekRes);
      setProgressMonth(progressMonthRes);
      setMetadata(metadataRes);
      setSummary(summaryRes ? (summaryRes as PlayerSummary) : null);

      if (statsRes.error === 'No data available' && !statsRes.fetched_at && !polling && pollAttemptsRef.current === 0) {
        setPolling(true);
        pollAttemptsRef.current = 1;
      }

      if (isPolling && statsRes.fetched_at && !statsRes.error) {
        setPolling(false);
        pollAttemptsRef.current = 0;
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      }
    } catch (err: unknown) {
      const errorMessage = extractErrorMessage(err, 'Failed to load player stats');
      setError(errorMessage);
      setPolling(false);
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    } finally {
      if (!isPolling) {
        setLoading(false);
      }
    }
  }, [username, polling]);

  useEffect(() => {
    setPolling(false);
    pollAttemptsRef.current = 0;
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    fetchData();
  }, [username, fetchData]);

  useEffect(() => {
    if (!polling || !username) {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      return;
    }

    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    pollingIntervalRef.current = setInterval(async () => {
      if (pollAttemptsRef.current >= MAX_POLL_ATTEMPTS) {
        setPolling(false);
        pollAttemptsRef.current = 0;
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        return;
      }

      pollAttemptsRef.current += 1;
      await fetchData(true);
    }, 2000);

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [polling, username, fetchData]);

  // Handle actions menu dropdown
  const handleActionsMenuToggle = () => {
    if (!isActionsMenuOpen && actionsMenuButtonRef.current) {
      const rect = actionsMenuButtonRef.current.getBoundingClientRect();
      setActionsMenuPosition({
        top: rect.bottom + 4,
        right: window.innerWidth - rect.right,
      });
    }
    setIsActionsMenuOpen(!isActionsMenuOpen);
  };

  useEffect(() => {
    if (!isActionsMenuOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        actionsMenuButtonRef.current &&
        !actionsMenuButtonRef.current.contains(event.target as Node) &&
        actionsMenuDropdownRef.current &&
        !actionsMenuDropdownRef.current.contains(event.target as Node)
      ) {
        setIsActionsMenuOpen(false);
        setActionsMenuPosition(null);
      }
    };

    const handleScroll = () => {
      setIsActionsMenuOpen(false);
      setActionsMenuPosition(null);
    };

    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('scroll', handleScroll, true);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [isActionsMenuOpen]);

  const handleActionClick = (action: () => void) => {
    action();
    setIsActionsMenuOpen(false);
    setActionsMenuPosition(null);
  };

  const handleRecalculateGameMode = async () => {
    if (!username) return;

    setRecalculatingGameMode(true);
    try {
      const updatedPlayer = await api.PlayersService.recalculateGameModeApiV1PlayersUsernameRecalculateGameModePost(username);

      // Refresh metadata to get updated game mode
      const metadataRes = await api.PlayersService.getPlayerMetadataApiV1PlayersUsernameMetadataGet(username).catch(() => null);
      if (metadataRes) {
        setMetadata(metadataRes);
      }

      const gameModeDisplay = updatedPlayer.game_mode
        ? (updatedPlayer.game_mode.charAt(0).toUpperCase() + updatedPlayer.game_mode.slice(1))
        : 'Unknown';
      showNotification(`Game mode recalculated: ${gameModeDisplay}`, 'success');
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to recalculate game mode');
      showNotification(errorMessage, 'error');
    } finally {
      setRecalculatingGameMode(false);
    }
  };

  const handleTriggerFetch = async () => {
    if (!username) return;

    setFetching(true);
    try {
      await api.PlayersService.triggerManualFetchApiV1PlayersUsernameFetchPost(username);
      showNotification('Fetch task enqueued successfully. Refreshing data...', 'success');
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
          // Silently fail - data refresh is optional
        }
      }, 2000);
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to trigger fetch');
      showNotification(errorMessage, 'error');
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
        90
      );
      setSkillProgress(skillData);
    } catch (err: unknown) {
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
        90
      );
      setBossProgress(bossData);
    } catch (err: unknown) {
      setBossProgress(null);
    } finally {
      setBossProgressLoading(false);
    }
  };

  const closeBossModal = () => {
    setSelectedBoss(null);
    setBossProgress(null);
  };

  const handleGenerateSummary = async () => {
    if (!metadata || !metadata.id) {
      showNotification('Player ID not available', 'error');
      return;
    }

    setGeneratingSummary(true);
    try {
      const response = await api.SystemService.generateSummariesApiV1SystemGenerateSummariesPost({
        player_id: metadata.id,
        force_regenerate: false,
      });

      showNotification(
        <div className="space-y-1">
          <p>{response.message}</p>
          <p className="text-sm text-secondary-500 dark:text-secondary-300">
            Summary generation task has been enqueued. The summary will appear here once generated.
          </p>
        </div>,
        'success'
      );

      setTimeout(async () => {
        if (username) {
          try {
            const summaryRes = await api.PlayersService.getPlayerSummaryApiV1PlayersUsernameSummaryGet(username).catch(() => null);
            if (summaryRes) {
              setSummary(summaryRes as PlayerSummary);
            }
          } catch (err) {
            // Silently fail - summary refresh is optional
          }
        }
      }, 5000);
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to generate summary');
      showNotification(errorMessage, 'error');
    } finally {
      setGeneratingSummary(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message={polling ? 'Fetching player stats...' : 'Loading...'} fullScreen />;
  }

  if (error || !stats) {
    return <ErrorDisplay error={error || 'Player not found'} />;
  }

  const bossNames = Object.keys(stats.bosses || {});

  const orderedSkills: OrderedSkill[] = OSRS_SKILL_ORDER
    .map((skillName) => {
      const skillData = stats.skills?.[skillName] as SkillData | undefined;
      return {
        name: skillName,
        displayName: skillName.charAt(0).toUpperCase() + skillName.slice(1),
        level: skillData?.level ?? 1,
        experience: skillData?.experience ?? 0,
        maxLevel: 99,
      };
    });

  const orderedBosses: OrderedBoss[] = bossNames
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
    .filter((boss): boss is OrderedBoss => boss !== null && boss.kills > 0)
    .sort((a, b) => b.kills - a.kills);

  // Calculate stats for cards
  const totalLevel = stats.overall?.level ?? 0;
  const totalXP = stats.overall?.experience ?? 0;
  const combatLevel = stats.combat_level ?? 0;
  const overallRank = stats.overall?.rank ?? null;

  // Calculate XP gained for different periods
  const xpGained7d = progressWeek?.progress.experience_gained.overall ?? 0;
  const levelsGained7d = progressWeek?.progress.levels_gained.overall ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900 dark:text-secondary-100 mb-2 flex items-center gap-2">
            {metadata && (
              <GameModeBadge gameMode={metadata.game_mode} size="lg" className="mr-1" />
            )}
            {stats.username}
            {polling && (
              <span className="ml-2 text-sm font-normal text-secondary-500 dark:text-secondary-300">
                (fetching...)
              </span>
            )}
          </h1>
          {stats.fetched_at && (
            <p className="text-sm text-secondary-500 dark:text-secondary-300">
              Last updated: {format(new Date(stats.fetched_at), 'MMM d, yyyy HH:mm')}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isAuthenticated && (
            <button
              onClick={handleTriggerFetch}
              disabled={fetching}
              className="btn btn-primary text-sm"
            >
              {fetching ? 'Updating...' : 'Update'}
            </button>
          )}
          <button
            ref={actionsMenuButtonRef}
            onClick={handleActionsMenuToggle}
            className="btn btn-secondary text-sm p-2 dark:bg-secondary-800 dark:text-secondary-200 dark:border-secondary-600 dark:hover:bg-secondary-700 dark:hover:text-secondary-100"
            aria-label="More actions"
            aria-expanded={isActionsMenuOpen}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
            </svg>
          </button>
          {isActionsMenuOpen && actionsMenuPosition && (
            <>
              {createPortal(
                <div
                  ref={actionsMenuDropdownRef}
                  className="fixed w-56 rounded-md shadow-lg bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-700 z-[9999]"
                  style={{
                    top: `${actionsMenuPosition.top}px`,
                    right: `${actionsMenuPosition.right}px`,
                  }}
                  role="menu"
                >
                  <div className="py-1">
                    <a
                      href={`https://secure.runescape.com/m=hiscore_oldschool/hiscorepersonal.ws?user1=${encodeURIComponent(stats.username)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full text-left px-4 py-2 text-sm text-secondary-900 dark:text-secondary-100 hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors flex items-center gap-2 whitespace-nowrap"
                      role="menuitem"
                      onClick={() => {
                        setIsActionsMenuOpen(false);
                        setActionsMenuPosition(null);
                      }}
                    >
                      <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                      View on OSRS
                    </a>
                    {isAuthenticated && metadata && (
                      <button
                        onClick={() => handleActionClick(handleRecalculateGameMode)}
                        disabled={recalculatingGameMode}
                        className="w-full text-left px-4 py-2 text-sm text-secondary-900 dark:text-secondary-100 hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                        role="menuitem"
                      >
                        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        {recalculatingGameMode ? 'Recalculating...' : 'Recalculate Game Mode'}
                      </button>
                    )}
                    {isAdmin && metadata && (
                      <button
                        onClick={() => handleActionClick(handleGenerateSummary)}
                        disabled={generatingSummary}
                        className="w-full text-left px-4 py-2 text-sm text-secondary-900 dark:text-secondary-100 hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                        role="menuitem"
                      >
                        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        {generatingSummary ? 'Generating...' : 'Generate Summary'}
                      </button>
                    )}
                  </div>
                </div>,
                document.body
              )}
            </>
          )}
        </div>
      </div>

      {/* Top Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
        <StatsCard
          title="Total Level"
          value={totalLevel}
          color="primary"
          icon={<span className="text-xl">📊</span>}
          trend={levelsGained7d > 0 ? {
            value: Math.round((levelsGained7d / totalLevel) * 100 * 100) / 100,
            label: `+${levelsGained7d} levels (7d)`
          } : undefined}
        />
        <StatsCard
          title="Total XP"
          value={totalXP >= 1000000 ? `${(totalXP / 1000000).toFixed(2)}M` : totalXP >= 1000 ? `${(totalXP / 1000).toFixed(1)}K` : formatNumberLocale(totalXP)}
          color="blue"
          icon={<span className="text-xl">⭐</span>}
          trend={xpGained7d > 0 ? {
            value: Math.round((xpGained7d / totalXP) * 100 * 100) / 100,
            label: `+${(xpGained7d / 1000000).toFixed(2)}M XP (7d)`
          } : undefined}
        />
        <StatsCard
          title="Combat Level"
          value={combatLevel}
          color="success"
          icon={<span className="text-xl">⚔️</span>}
        />
        <StatsCard
          title="Overall Rank"
          value={overallRank ? formatNumberLocale(overallRank) : 'N/A'}
          color="purple"
          icon={<span className="text-xl">🏆</span>}
        />
      </div>

      {/* Progress Summary Card */}
      {summary && <ProgressSummary summary={summary} />}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {username && (
          <div className="card bg-white dark:bg-secondary-800">
            <OverallXPGraph username={username} />
          </div>
        )}
        {progressWeek && (
          <div className="card bg-white dark:bg-secondary-800">
            <TopSkillsChart progressWeek={progressWeek} />
          </div>
        )}
      </div>

      {/* Skills and Progress Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="card bg-white dark:bg-secondary-800 flex flex-col">
            <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">
              Skills Overview
            </h3>
            <div className="flex items-start">
              <SkillsGrid
                skills={orderedSkills}
                skillIcons={SKILL_ICONS}
                totalLevel={totalLevel}
                onSkillClick={handleSkillClick}
              />
            </div>
          </div>
        </div>
        <div className="lg:col-span-1">
          <div className="card bg-white dark:bg-secondary-800 flex flex-col">
            <TopSkillsList progressWeek={progressWeek} onSkillClick={handleSkillClick} />
          </div>
        </div>
        <div className="lg:col-span-1">
          <div className="card bg-white dark:bg-secondary-800 flex flex-col">
            <TopBossesList
              progressWeek={progressWeek}
              orderedBosses={orderedBosses}
              onBossClick={handleBossClick}
            />
          </div>
        </div>
      </div>

      {/* Skills Progress Table */}
      <SkillsProgressTable
        progressDay={progressDay}
        progressWeek={progressWeek}
        progressMonth={progressMonth}
        orderedSkills={orderedSkills}
        onSkillClick={handleSkillClick}
      />

      {/* Boss Progress Summary */}
      {orderedBosses.length > 0 && (
        <BossProgressTable
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
            className="card max-w-4xl w-full max-h-[90vh] overflow-y-auto bg-white dark:bg-secondary-800"
            onClick={(e) => e.stopPropagation()}
          >
            {skillProgressLoading ? (
              <div className="p-8 text-center">
                <div className="text-secondary-600 dark:text-secondary-200 text-xl">Loading skill details...</div>
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
                  <h2 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
                    {selectedSkill.charAt(0).toUpperCase() + selectedSkill.slice(1)}
                  </h2>
                  <button
                    onClick={closeSkillModal}
                    className="text-secondary-500 dark:text-secondary-300 hover:text-secondary-700 dark:hover:text-secondary-100 text-3xl leading-none"
                  >
                    ×
                  </button>
                </div>
                <div className="text-secondary-600 dark:text-secondary-200">Failed to load skill progress data.</div>
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
            className="card max-w-4xl w-full max-h-[90vh] overflow-y-auto bg-white dark:bg-secondary-800"
            onClick={(e) => e.stopPropagation()}
          >
            {bossProgressLoading ? (
              <div className="p-8 text-center">
                <div className="text-secondary-600 dark:text-secondary-200 text-xl">Loading boss details...</div>
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
                  <h2 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
                    {selectedBoss.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </h2>
                  <button
                    onClick={closeBossModal}
                    className="text-secondary-500 dark:text-secondary-300 hover:text-secondary-700 dark:hover:text-secondary-100 text-3xl leading-none"
                  >
                    ×
                  </button>
                </div>
                <div className="text-secondary-600 dark:text-secondary-200">Failed to load boss progress data.</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Player Metadata */}
      {metadata && <PlayerMetadata metadata={metadata} />}
    </div>
  );
};
