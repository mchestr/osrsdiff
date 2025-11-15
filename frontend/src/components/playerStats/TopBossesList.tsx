import type { ProgressAnalysisResponse } from '../../api/models/ProgressAnalysisResponse';
import type { OrderedBoss } from '../../types/player';

interface TopBossesListProps {
  progressWeek: ProgressAnalysisResponse | null;
  orderedBosses: OrderedBoss[];
  onBossClick: (bossName: string) => void;
}

export const TopBossesList: React.FC<TopBossesListProps> = ({
  progressWeek,
  orderedBosses,
  onBossClick,
}) => {
  const topBossesData = progressWeek
    ? Object.entries(progressWeek.progress.boss_kills_gained || {})
        .map(([boss, kills]) => ({
          boss,
          kills: typeof kills === 'number' ? kills : 0,
        }))
        .filter((item) => item.kills > 0)
        .sort((a, b) => b.kills - a.kills)
        .slice(0, 10)
        .map((item) => {
          const bossData = orderedBosses.find((b) => b.name === item.boss);
          return {
            ...item,
            displayName: bossData?.displayName || item.boss.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
          };
        })
    : [];

  return (
    <>
      <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">
        Top Bosses Progress (7d)
      </h3>
      {topBossesData.length > 0 ? (
        <div className="space-y-3 max-h-[520px] overflow-y-auto">
          {topBossesData.map((bossData, index) => (
            <div
              key={bossData.boss}
              className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors cursor-pointer"
              onClick={() => {
                const bossName = bossData.boss.toLowerCase().replace(/\s+/g, '_');
                onBossClick(bossName);
              }}
            >
              <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-success-100 dark:bg-success-900/50 rounded-lg text-xs font-bold text-success-600 dark:text-success-400">
                #{index + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-secondary-900 dark:text-secondary-100 capitalize truncate">
                    {bossData.displayName}
                  </span>
                  <span className="text-sm font-medium text-green-600 dark:text-green-400 whitespace-nowrap">
                    +{bossData.kills.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-secondary-500 dark:text-secondary-300">
            No boss progress data available
          </div>
        </div>
      )}
    </>
  );
};

