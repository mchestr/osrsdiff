import { ApexOptions } from 'apexcharts';
import { format } from 'date-fns';
import { useEffect, useState } from 'react';
import Chart from 'react-apexcharts';
import { api } from '../api/apiClient';
import type { SkillProgressResponse } from '../api/models/SkillProgressResponse';
import { useTheme } from '../contexts/ThemeContext';
import { getChartColors, getXAxisLabelColors } from '../utils/chartColors';

interface OverallXPGraphProps {
  username: string;
}

export const OverallXPGraph: React.FC<OverallXPGraphProps> = ({ username }) => {
  const { theme } = useTheme();
  const colors = getChartColors(theme);
  const [progress, setProgress] = useState<SkillProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!username) return;

      try {
        setLoading(true);
        setError(null);
        // Fetch overall XP progress (90 days of history)
        const data = await api.HistoryService.getSkillProgressApiV1PlayersUsernameHistorySkillsSkillGet(
          username,
          'overall',
          90
        );
        setProgress(data);
      } catch (err: unknown) {
        console.error('Failed to load overall XP progress:', err);
        setError('Failed to load XP data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [username]);

  if (loading) {
    return (
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-200 mb-4">Overall XP</h3>
        <div className="text-secondary-500 dark:text-secondary-300 text-sm text-center py-8">Loading...</div>
      </div>
    );
  }

  if (error || !progress || !progress.timeline || progress.timeline.length === 0) {
    return (
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-200 mb-4">Overall XP</h3>
        <div className="text-secondary-500 dark:text-secondary-300 text-sm text-center py-8">
          {error || 'No data available'}
        </div>
      </div>
    );
  }

  // Prepare timeline data for chart
  const timelineData = progress.timeline.map((entry) => ({
    date: format(new Date(entry.date), 'MMM d'),
    experience: entry.experience ?? 0,
    level: entry.level ?? 0,
  }));

  const currentXP = progress.timeline[progress.timeline.length - 1]?.experience ?? 0;
  const xpGained = progress.progress.experience_gained ?? 0;

  // Filter to show only every 7th day
  const filteredData = timelineData.filter((_, index) => index % 7 === 0 || index === timelineData.length - 1);

  const categories = filteredData.map((d) => d.date);
  const experienceData = filteredData.map((d) => d.experience);

  const options: ApexOptions = {
    legend: {
      show: false,
    },
    colors: [colors.primary],
    chart: {
      fontFamily: 'Inter, sans-serif',
      height: 350,
      type: 'area',
      toolbar: {
        show: false,
      },
      zoom: {
        enabled: false,
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
        stops: [0, 100],
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
          if (value >= 1000000) return `${(value / 1000000).toFixed(2)}M XP`;
          if (value >= 1000) return `${(value / 1000).toFixed(1)}K XP`;
          return `${value} XP`;
        },
      },
    },
    xaxis: {
      type: 'category',
      categories,
      axisBorder: {
        show: false,
      },
      axisTicks: {
        show: false,
      },
      labels: {
        style: {
          fontSize: '12px',
          colors: getXAxisLabelColors(categories.length, theme),
        },
        rotate: -45,
        rotateAlways: true,
        maxHeight: 100,
        hideOverlappingLabels: true,
      },
      tooltip: {
        enabled: false,
      },
    },
    yaxis: {
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
      title: {
        text: '',
        style: {
          fontSize: '0px',
        },
      },
    },
  };

  const series = [
    {
      name: 'Experience',
      data: experienceData,
    },
  ];

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-2">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-200">Overall XP</h3>

        {/* Current Stats */}
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs text-secondary-500 dark:text-secondary-300">Total XP</span>
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-200">
              {currentXP ? (currentXP / 1000000).toFixed(2) + 'M' : 'N/A'}
            </span>
          </div>
          {xpGained > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-secondary-500 dark:text-secondary-300">Gained (90d)</span>
              <span className="text-sm font-medium text-green-600 dark:text-green-400">
                +{(xpGained / 1000000).toFixed(2)}M
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Graph */}
      <div className="max-w-full overflow-x-auto">
        <div id="overall-xp-chart" className="min-w-[600px]">
          <Chart key={theme} options={options} series={series} type="area" height={350} />
        </div>
      </div>
    </div>
  );
};

