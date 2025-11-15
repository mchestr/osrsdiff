import { ApexOptions } from 'apexcharts';
import { format } from 'date-fns';
import Chart from 'react-apexcharts';
import type { SkillProgressResponse } from '../../api/models/SkillProgressResponse';
import { useTheme } from '../../hooks';
import type { SkillData } from '../../types/player';
import { getChartColors, getXAxisLabelColors } from '../../utils/chartColors';
import { formatDuration, getExpToMax, getExpToNextLevel } from '../../utils/osrs';

interface SkillDetailModalProps {
  skill: string;
  skillData: SkillData | undefined;
  skillProgress: SkillProgressResponse;
  skillIcon: string | undefined;
  onClose: () => void;
}

export const SkillDetailModal: React.FC<SkillDetailModalProps> = ({
  skill,
  skillData,
  skillProgress,
  skillIcon,
  onClose,
}) => {
  const { theme } = useTheme();
  const colors = getChartColors(theme);
  const currentLevel = skillData?.level ?? 1;
  const currentExp = skillData?.experience ?? 0;
  const maxLevel = 99;
  const isMaxLevel = currentLevel >= maxLevel;

  const dailyRate = skillProgress.progress.daily_experience_rate;
  const expToNextLevel = isMaxLevel ? 0 : getExpToNextLevel(currentLevel, currentExp);
  const expToMax = isMaxLevel ? 0 : getExpToMax(currentLevel, currentExp);

  const timeToNextLevel = dailyRate > 0 && !isMaxLevel
    ? formatDuration(expToNextLevel / dailyRate)
    : isMaxLevel ? 'Max level reached!' : 'Insufficient data';

  const timeToMax = dailyRate > 0 && !isMaxLevel
    ? formatDuration(expToMax / dailyRate)
    : isMaxLevel ? 'Max level reached!' : 'Insufficient data';

  const timelineData = skillProgress.timeline.map((entry) => ({
    date: format(new Date(entry.date), 'MMM d'),
    level: entry.level ?? 0,
    experience: entry.experience ?? 0,
  }));

  // Filter to show only every 7th day (keep first, every 7th, and last)
  const filteredTimelineData = timelineData.filter((_, index) => index % 7 === 0 || index === timelineData.length - 1);

  return (
    <div className="p-6">
      <div className="flex justify-between items-start mb-6">
        <div className="flex items-center gap-4">
          {skillIcon && skillIcon !== '⚓' ? (
            <img src={skillIcon} alt={skill} className="w-12 h-12" />
          ) : (
            <span className="text-4xl">{skillIcon || '❓'}</span>
          )}
          <div>
            <h2 className="text-3xl font-bold text-secondary-900 dark:text-secondary-100">
              {skill.charAt(0).toUpperCase() + skill.slice(1)}
            </h2>
            <p className="text-sm text-secondary-500 dark:text-secondary-300">
              {skillProgress.period_days} days of history • {skillProgress.total_records} records
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-secondary-500 dark:text-secondary-300 hover:text-secondary-700 dark:hover:text-secondary-100 text-3xl leading-none"
        >
          ×
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="card bg-white dark:bg-secondary-800">
          <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Current Level</h3>
          <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            {currentLevel}/{maxLevel}
          </p>
        </div>
        <div className="card bg-white dark:bg-secondary-800">
          <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Experience</h3>
          <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            {currentExp.toLocaleString()}
          </p>
        </div>
        <div className="card bg-white dark:bg-secondary-800">
          <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Daily XP Rate</h3>
          <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            {dailyRate > 0 ? Math.round(dailyRate).toLocaleString() : 'N/A'}
          </p>
        </div>
        <div className="card bg-white dark:bg-secondary-800">
          <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Levels Gained</h3>
          <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            {skillProgress.progress.levels_gained}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="card bg-white dark:bg-secondary-800">
          <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-2 uppercase tracking-wide">Time to Next Level</h3>
          <div className="space-y-1">
            <p className="text-xl font-bold text-secondary-900 dark:text-secondary-100">{timeToNextLevel}</p>
            {!isMaxLevel && dailyRate > 0 && (
              <p className="text-sm text-secondary-500 dark:text-secondary-300">
                {expToNextLevel.toLocaleString()} XP needed
              </p>
            )}
          </div>
        </div>
        <div className="card bg-white dark:bg-secondary-800">
          <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-2 uppercase tracking-wide">Time to Max Level</h3>
          <div className="space-y-1">
            <p className="text-xl font-bold text-secondary-900 dark:text-secondary-100">{timeToMax}</p>
            {!isMaxLevel && dailyRate > 0 && (
              <p className="text-sm text-secondary-500 dark:text-secondary-300">
                {expToMax.toLocaleString()} XP needed
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="card bg-white dark:bg-secondary-800 mb-6">
        <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">
          Progress Summary ({skillProgress.period_days} days)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Experience Gained</p>
            <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
              {skillProgress.progress.experience_gained.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Average Daily XP</p>
            <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
              {Math.round(skillProgress.progress.daily_experience_rate).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {timelineData.length > 0 && (
        <div className="card bg-white dark:bg-secondary-800">
          <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">Experience History</h3>
          <div className="max-w-full overflow-x-auto">
            <div id="skill-history-chart" className="min-w-[600px]">
              <Chart
                key={theme}
                options={{
                  legend: {
                    show: true,
                    position: 'top',
                    horizontalAlign: 'left',
                    labels: {
                      colors: colors.legendLabels,
                    },
                  },
                  colors: [colors.primary, colors.secondary],
                  chart: {
                    fontFamily: 'Inter, sans-serif',
                    height: 400,
                    type: 'line',
                    toolbar: {
                      show: false,
                    },
                  },
                  stroke: {
                    curve: 'straight',
                    width: [2, 4],
                    colors: [colors.primary, colors.secondary],
                    dashArray: [0, 0],
                  },
                  fill: {
                    type: 'solid',
                    opacity: [0.55],
                  },
                  markers: {
                    size: 1,
                  },
                  grid: {
                    xaxis: {
                      lines: {
                        show: false,
                      },
                    },
                    yaxis: {
                      lines: {
                        show: true,
                      },
                    },
                    strokeDashArray: 3,
                    borderColor: colors.gridBorder,
                  },
                  dataLabels: {
                    enabled: false,
                  },
                  tooltip: {
                    enabled: true,
                    theme: colors.tooltipTheme,
                    style: {
                      fontSize: '12px',
                      fontFamily: 'Inter, sans-serif',
                    },
                    y: {
                      formatter: (value: number, { seriesIndex }: { seriesIndex: number }) => {
                        if (seriesIndex === 0) {
                          // Experience
                          if (value >= 1000000) return `${(value / 1000000).toFixed(2)}M XP`;
                          if (value >= 1000) return `${(value / 1000).toFixed(1)}K XP`;
                          return `${value.toLocaleString()} XP`;
                        } else {
                          // Level
                          return `Level ${value}`;
                        }
                      },
                    },
                  },
                  xaxis: {
                    type: 'category',
                    categories: filteredTimelineData.map((d) => d.date),
                    axisBorder: {
                      show: false,
                    },
                    axisTicks: {
                      show: false,
                    },
                    labels: {
                      style: {
                        fontSize: '12px',
                        colors: getXAxisLabelColors(filteredTimelineData.length, theme),
                      },
                      rotate: -45,
                      rotateAlways: true,
                      maxHeight: 100,
                      hideOverlappingLabels: true,
                    },
                  },
                  yaxis: [
                    {
                      title: {
                        text: 'Experience',
                        style: {
                          fontSize: '14px',
                          fontWeight: 600,
                          color: colors.axisTitle,
                        },
                      },
                      labels: {
                        style: {
                          fontSize: '12px',
                          colors: [colors.yAxisLabels],
                        },
                        formatter: (value: number) => {
                          if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
                          if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
                          return value.toString();
                        },
                      },
                    },
                    {
                      opposite: true,
                      title: {
                        text: 'Level',
                        style: {
                          fontSize: '14px',
                          fontWeight: 600,
                          color: colors.axisTitle,
                        },
                      },
                      labels: {
                        style: {
                          fontSize: '12px',
                          colors: [colors.yAxisLabels],
                        },
                      },
                    },
                  ],
                } as ApexOptions}
                series={[
                  {
                    name: 'Experience',
                    type: 'area',
                    data: filteredTimelineData.map((d) => d.experience),
                  },
                  {
                    name: 'Level',
                    type: 'line',
                    data: filteredTimelineData.map((d) => d.level),
                  },
                ]}
                height={400}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

