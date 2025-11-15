import { useState } from 'react';
import type { ProgressAnalysisResponse } from '../../api/models/ProgressAnalysisResponse';
import type { OrderedBoss } from '../../types/player';

interface BossProgressTableProps {
  progressDay: ProgressAnalysisResponse | null;
  progressWeek: ProgressAnalysisResponse | null;
  progressMonth: ProgressAnalysisResponse | null;
  orderedBosses: OrderedBoss[];
  onBossClick: (bossName: string) => void;
}

export const BossProgressTable: React.FC<BossProgressTableProps> = ({
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
    <div className="card bg-white dark:bg-gray-800">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-200">Boss Progress Summary</h2>
        <select
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(Number(e.target.value))}
          className="input text-sm bg-white dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600"
        >
          <option value={1} className="dark:bg-gray-700 dark:text-gray-200">Last 1 Day</option>
          <option value={7} className="dark:bg-gray-700 dark:text-gray-200">Last 7 Days</option>
          <option value={30} className="dark:bg-gray-700 dark:text-gray-200">Last 30 Days</option>
        </select>
      </div>

      {currentProgress ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
          {orderedBosses.map((boss) => {
            const progress = getBossProgress(boss.name);
            return (
              <div
                key={boss.name}
                className={`p-4 rounded-lg border-2 cursor-pointer hover:shadow-md transition-all ${
                  progress.kills > 0
                    ? 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800'
                    : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600'
                }`}
                onClick={() => onBossClick(boss.name)}
              >
                <div className="text-xs font-semibold text-gray-900 dark:text-gray-200 text-center mb-2 leading-tight">
                  {boss.displayName}
                </div>
                <div className="text-xl font-bold text-gray-900 dark:text-gray-200 text-center mb-1">
                  {boss.kills.toLocaleString()}
                </div>
                {progress.kills > 0 ? (
                  <div className="text-xs font-semibold text-green-600 dark:text-green-400 text-center">
                    +{progress.kills.toLocaleString()} ({getPeriodLabel(selectedPeriod)})
                  </div>
                ) : (
                  <div className="text-xs text-secondary-500 dark:text-secondary-300 text-center">
                    0 ({getPeriodLabel(selectedPeriod)})
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-8 text-secondary-500 dark:text-secondary-300">
          No progress data available for the selected period
        </div>
      )}
    </div>
  );
};

