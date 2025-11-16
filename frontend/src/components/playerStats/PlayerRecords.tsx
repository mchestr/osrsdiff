import { format } from 'date-fns';
import { useState } from 'react';
import { SKILL_ICONS } from '../../utils/skillIcons';
import { formatNumberLocale } from '../../utils/formatters';

interface SkillRecord {
  skill: string;
  exp_gain: number;
  date: string;
  start_exp: number;
  end_exp: number;
}

interface PeriodRecords {
  day: Record<string, SkillRecord>;
  week: Record<string, SkillRecord>;
  month: Record<string, SkillRecord>;
  year: Record<string, SkillRecord>;
}

interface PlayerRecordsProps {
  records: PeriodRecords | null;
}

type PeriodType = 'day' | 'week' | 'month' | 'year';

export const PlayerRecords: React.FC<PlayerRecordsProps> = ({ records }) => {
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('week');

  if (!records) {
    return (
      <div className="card bg-white dark:bg-gray-800">
        <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">
          Records
        </h2>
        <div className="text-center text-secondary-500 dark:text-secondary-300 py-8">
          No records data available
        </div>
      </div>
    );
  }

  const periodLabels: Record<PeriodType, string> = {
    day: 'Day',
    week: 'Week',
    month: 'Month',
    year: 'Year',
  };

  const selectedRecords = records[selectedPeriod] || {};

  // Convert to array and sort by exp gain
  const recordsArray = Object.entries(selectedRecords)
    .map(([skillName, record]) => ({
      skill: skillName,
      displayName: skillName.charAt(0).toUpperCase() + skillName.slice(1),
      exp_gain: record.exp_gain,
      date: record.date,
      start_exp: record.start_exp,
      end_exp: record.end_exp,
    }))
    .filter((item) => item.exp_gain > 0)
    .sort((a, b) => b.exp_gain - a.exp_gain);

  return (
    <div className="card bg-white dark:bg-gray-800">
      <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">
        Records
      </h2>

      {/* Period selector */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {(['day', 'week', 'month', 'year'] as PeriodType[]).map((period) => (
          <button
            key={period}
            onClick={() => setSelectedPeriod(period)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedPeriod === period
                ? 'bg-primary-500 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-secondary-700 dark:text-secondary-200 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            {periodLabels[period]}
          </button>
        ))}
      </div>

      {/* Records list */}
      {recordsArray.length > 0 ? (
        <div className="space-y-3 max-h-[520px] overflow-y-auto">
          {recordsArray.map((record, index) => {
            const iconUrl = SKILL_ICONS[record.skill];
            const recordDate = new Date(record.date);

            return (
              <div
                key={record.skill}
                className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
              >
                <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-primary-100 dark:bg-primary-900/50 rounded-lg text-xs font-bold text-primary-600 dark:text-primary-400">
                  #{index + 1}
                </div>
                {iconUrl && iconUrl !== '⚓' ? (
                  <img
                    src={iconUrl}
                    alt={record.displayName}
                    className="w-8 h-8 flex-shrink-0"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                    }}
                  />
                ) : (
                  <span className="w-8 h-8 flex items-center justify-center text-lg">
                    {iconUrl || '❓'}
                  </span>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-semibold text-secondary-900 dark:text-secondary-100 capitalize truncate">
                      {record.displayName}
                    </span>
                    <span className="text-sm font-medium text-secondary-700 dark:text-secondary-200 whitespace-nowrap">
                      {formatNumberLocale(record.exp_gain)} XP
                    </span>
                  </div>
                  <div className="text-xs text-secondary-500 dark:text-secondary-300">
                    {format(recordDate, 'MMM d, yyyy')}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center py-8">
          <div className="text-center text-secondary-500 dark:text-secondary-300">
            No records available for this period
          </div>
        </div>
      )}
    </div>
  );
};

