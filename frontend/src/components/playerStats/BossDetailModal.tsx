import { format } from 'date-fns';
import Chart from 'react-apexcharts';
import { ApexOptions } from 'apexcharts';
import type { BossProgressResponse } from '../../api/models/BossProgressResponse';
import type { BossData } from '../../types/player';
import { useTheme } from '../../hooks';
import { getChartColors, getXAxisLabelColors } from '../../utils/chartColors';

interface BossDetailModalProps {
  boss: string;
  bossData: BossData | undefined;
  bossProgress: BossProgressResponse;
  onClose: () => void;
}

export const BossDetailModal: React.FC<BossDetailModalProps> = ({
  boss,
  bossData,
  bossProgress,
  onClose,
}) => {
  const { theme } = useTheme();
  const colors = getChartColors(theme);
  const currentKills = bossData?.kc ?? 0;
  const dailyRate = bossProgress.progress.daily_kill_rate;

  const timelineData = bossProgress.timeline.map((entry) => ({
    date: format(new Date(entry.date), 'MMM d'),
    kc: entry.kc ?? 0,
  }));

  // Filter to show only every 7th day (keep first, every 7th, and last)
  const filteredTimelineData = timelineData.filter((_, index) => index % 7 === 0 || index === timelineData.length - 1);

  return (
    <div className="p-6">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-3xl font-bold text-secondary-900 dark:text-secondary-100">
            {boss.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
          </h2>
          <p className="text-sm text-secondary-500 dark:text-secondary-300">
            {bossProgress.period_days} days of history • {bossProgress.total_records} records
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-secondary-500 dark:text-secondary-300 hover:text-secondary-700 dark:hover:text-secondary-100 text-3xl leading-none"
        >
          ×
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="card bg-white dark:bg-gray-800">
          <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Current Kills</h3>
          <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            {currentKills.toLocaleString()}
          </p>
        </div>
        <div className="card bg-white dark:bg-gray-800">
          <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Daily Kill Rate</h3>
          <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            {dailyRate > 0 ? Math.round(dailyRate).toLocaleString() : 'N/A'}
          </p>
        </div>
        <div className="card bg-white dark:bg-gray-800">
          <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Kills Gained</h3>
          <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            {bossProgress.progress.kills_gained.toLocaleString()}
          </p>
        </div>
        {bossData?.rank && (
          <div className="card bg-white dark:bg-gray-800">
            <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Rank</h3>
            <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
              {bossData.rank.toLocaleString()}
            </p>
          </div>
        )}
      </div>

      <div className="card bg-white dark:bg-gray-800 mb-6">
        <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">
          Progress Summary ({bossProgress.period_days} days)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Kills Gained</p>
            <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
              {bossProgress.progress.kills_gained.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Average Daily Kills</p>
            <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
              {Math.round(bossProgress.progress.daily_kill_rate).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {timelineData.length > 0 && (
        <div className="card bg-white dark:bg-gray-800">
          <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">Kill Count History</h3>
          <div className="max-w-full overflow-x-auto">
            <div id="boss-history-chart" className="min-w-[600px]">
              <Chart
                key={theme}
                options={{
                  legend: {
                    show: false,
                  },
                  colors: [colors.primary],
                  chart: {
                    fontFamily: 'Inter, sans-serif',
                    height: 400,
                    type: 'area',
                    toolbar: {
                      show: false,
                    },
                  },
                  stroke: {
                    curve: 'straight',
                    width: 2,
                  },
                  fill: {
                    type: 'gradient',
                    gradient: {
                      opacityFrom: 0.55,
                      opacityTo: 0,
                    },
                  },
                  markers: {
                    size: 0,
                    strokeColors: '#fff',
                    strokeWidth: 2,
                    hover: {
                      size: 6,
                    },
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
                      formatter: (value: number) => {
                        return `${value.toLocaleString()} kills`;
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
                  yaxis: {
                    title: {
                      text: 'Kill Count',
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
                } as ApexOptions}
                series={[
                  {
                    name: 'Kill Count',
                    data: filteredTimelineData.map((d) => d.kc),
                  },
                ]}
                type="area"
                height={400}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

