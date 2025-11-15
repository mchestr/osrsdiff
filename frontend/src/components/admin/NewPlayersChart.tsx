import { ApexOptions } from 'apexcharts';
import { format, subDays, startOfDay } from 'date-fns';
import { useMemo } from 'react';
import Chart from 'react-apexcharts';
import type { PlayerResponse } from '../../api/models/PlayerResponse';
import { useTheme } from '../../hooks';
import { getChartColors } from '../../utils/chartColors';

interface NewPlayersChartProps {
  players: PlayerResponse[];
}

export const NewPlayersChart: React.FC<NewPlayersChartProps> = ({ players }) => {
  const { theme } = useTheme();
  const chartColors = getChartColors(theme);

  // Calculate data for last 30 days
  const chartData = useMemo(() => {
    const today = startOfDay(new Date());

    // Initialize all days with 0
    const dailyCounts: Record<string, number> = {};
    for (let i = 29; i >= 0; i--) {
      const date = subDays(today, i);
      const dateKey = format(date, 'yyyy-MM-dd');
      dailyCounts[dateKey] = 0;
    }

    // Count players created on each day
    players.forEach((player) => {
      // Parse the date string and extract just the date part (YYYY-MM-DD)
      // This avoids timezone issues by working with date strings directly
      const createdDateStr = player.created_at;
      let dateKey: string;

      // Handle ISO date strings (e.g., "2024-01-15T10:30:00Z" or "2024-01-15T10:30:00")
      if (createdDateStr.includes('T')) {
        dateKey = createdDateStr.split('T')[0];
      } else {
        // If it's already just a date string, use it directly
        dateKey = createdDateStr.split(' ')[0];
      }

      // Only count if within the last 30 days (inclusive)
      if (dailyCounts[dateKey] !== undefined) {
        dailyCounts[dateKey]++;
      }
    });

    // Convert to arrays for chart, sorted by date (oldest first)
    const sortedDates = Object.keys(dailyCounts).sort();
    const categories = sortedDates.map((date) => format(new Date(date), 'MMM d'));
    const data = sortedDates.map((date) => dailyCounts[date]);

    return { categories, data };
  }, [players]);

  const options: ApexOptions = useMemo(() => ({
    chart: {
      type: 'bar',
      fontFamily: 'Inter, sans-serif',
      height: 350,
      toolbar: {
        show: false,
      },
    },
    colors: [chartColors.primary],
    plotOptions: {
      bar: {
        borderRadius: 4,
        columnWidth: '60%',
      },
    },
    dataLabels: {
      enabled: false,
    },
    stroke: {
      show: true,
      width: 0,
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
      borderColor: chartColors.gridBorder,
    },
    xaxis: {
      categories: chartData.categories,
      labels: {
        style: {
          fontSize: '12px',
          colors: chartColors.xAxisLabels,
        },
        rotate: -45,
        rotateAlways: true,
      },
      axisBorder: {
        show: false,
      },
      axisTicks: {
        show: false,
      },
    },
    yaxis: {
      labels: {
        style: {
          fontSize: '12px',
          colors: chartColors.yAxisLabels,
        },
      },
      title: {
        text: 'New Players',
        style: {
          fontSize: '12px',
          color: chartColors.yAxisLabels,
        },
      },
    },
    tooltip: {
      theme: chartColors.tooltipTheme,
      style: {
        fontSize: '12px',
        fontFamily: 'Inter, sans-serif',
      },
      y: {
        formatter: (value: number) => `${value} ${value === 1 ? 'player' : 'players'}`,
      },
    },
  }), [chartData, chartColors]);

  const series = useMemo(() => [
    {
      name: 'New Players',
      data: chartData.data,
    },
  ], [chartData]);

  if (chartData.data.every((count) => count === 0)) {
    return (
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/[0.05] dark:bg-white/[0.03] p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          New Players (Last 30 Days)
        </h3>
        <div className="flex items-center justify-center h-[350px] text-gray-500 dark:text-gray-400">
          <p>No new players added in the last 30 days</p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/[0.05] dark:bg-white/[0.03] p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        New Players (Last 30 Days)
      </h3>
      <Chart
        options={options}
        series={series}
        type="bar"
        height={350}
      />
    </div>
  );
};

