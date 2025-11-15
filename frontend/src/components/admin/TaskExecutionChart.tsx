import { ApexOptions } from 'apexcharts';
import { format } from 'date-fns';
import { useMemo } from 'react';
import Chart from 'react-apexcharts';
import type { TaskExecutionResponse } from '../../api/models/TaskExecutionResponse';
import { useTheme } from '../../hooks';
import { getChartColors } from '../../utils/chartColors';
import { STATUS_COLORS } from './utils';

interface TaskExecutionChartProps {
  executions: TaskExecutionResponse[];
}

interface TimeBucket {
  time: string;
  total: number;
  success: number;
  failure: number;
  retry: number;
  other: number;
}

export const TaskExecutionChart: React.FC<TaskExecutionChartProps> = ({ executions }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const chartColors = getChartColors(theme);

  const timeSeriesData = useMemo(() => {
    if (executions.length === 0) return [];

    // Sort executions by started_at
    const sorted = [...executions].sort((a, b) =>
      new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
    );

    // Determine time grouping based on data range
    const firstTime = new Date(sorted[0].started_at).getTime();
    const lastTime = new Date(sorted[sorted.length - 1].started_at).getTime();
    const timeRange = lastTime - firstTime;
    const daysRange = timeRange / (1000 * 60 * 60 * 24);

    // Group by hour if less than 7 days, otherwise by day
    const groupByHour = daysRange < 7;

    // Create time buckets
    const timeBuckets: Record<string, TimeBucket> = {};

    sorted.forEach((execution) => {
      const date = new Date(execution.started_at);
      let bucketKey: string;

      if (groupByHour) {
        // Group by hour - use more compact format
        bucketKey = format(date, 'MMM d HH:mm');
      } else {
        // Group by day - use more compact format
        bucketKey = format(date, 'MMM d');
      }

      if (!timeBuckets[bucketKey]) {
        timeBuckets[bucketKey] = {
          time: bucketKey,
          total: 0,
          success: 0,
          failure: 0,
          retry: 0,
          other: 0,
        };
      }

      timeBuckets[bucketKey].total++;
      const status = execution.status || 'unknown';
      if (status === 'success') {
        timeBuckets[bucketKey].success++;
      } else if (status === 'failure') {
        timeBuckets[bucketKey].failure++;
      } else if (status === 'retry') {
        timeBuckets[bucketKey].retry++;
      } else {
        timeBuckets[bucketKey].other++;
      }
    });

    return Object.values(timeBuckets);
  }, [executions]);

  // All hooks must be called before any conditional returns
  const categories = useMemo(() => timeSeriesData.map((d) => d.time), [timeSeriesData]);

  const options: ApexOptions = useMemo(() => {
    if (timeSeriesData.length === 0) {
      return {} as ApexOptions;
    }
    return {
      chart: {
        type: 'line',
        fontFamily: 'Inter, sans-serif',
        height: 350,
        toolbar: {
          show: false,
        },
      },
      colors: ['#ffd700', STATUS_COLORS.success, STATUS_COLORS.failure, STATUS_COLORS.retry],
      stroke: {
        curve: 'smooth',
        width: 2,
      },
      markers: {
        size: 3,
        strokeWidth: 0,
        hover: {
          size: 5,
        },
      },
      xaxis: {
        categories,
        labels: {
          style: {
            fontSize: '9px',
            colors: chartColors.xAxisLabels,
          },
          rotate: -45,
          rotateAlways: true,
        },
        axisBorder: {
          show: true,
          color: chartColors.gridBorder,
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
      },
      grid: {
        borderColor: chartColors.gridBorder,
        strokeDashArray: 3,
        opacity: 0.3,
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
      },
      legend: {
        fontSize: '11px',
        labels: {
          colors: chartColors.legendLabels,
        },
      },
      tooltip: {
        theme: chartColors.tooltipTheme,
        style: {
          fontSize: '12px',
          fontFamily: 'Inter, sans-serif',
        },
      },
    };
  }, [categories, chartColors, timeSeriesData]);

  const series = useMemo(() => {
    if (timeSeriesData.length === 0) return [];
    return [
      {
        name: 'Total',
        data: timeSeriesData.map((d) => d.total),
      },
      {
        name: 'Success',
        data: timeSeriesData.map((d) => d.success),
      },
      {
        name: 'Failure',
        data: timeSeriesData.map((d) => d.failure),
      },
      {
        name: 'Retry',
        data: timeSeriesData.map((d) => d.retry),
      },
    ];
  }, [timeSeriesData]);

  // Early return after all hooks are called
  if (timeSeriesData.length === 0) {
    return null;
  }

  return (
    <>
      <style>
        {`
          .apexcharts-tooltip.apexcharts-theme-${isDark ? 'dark' : 'light'} {
            background-color: ${isDark ? '#2d2418' : '#ffffff'} !important;
            border: 2px solid ${isDark ? '#a68b5b' : '#d1d5db'} !important;
            color: ${isDark ? '#ffd700' : '#111827'} !important;
          }
          .apexcharts-tooltip.apexcharts-theme-${isDark ? 'dark' : 'light'} .apexcharts-tooltip-title {
            background-color: ${isDark ? '#2d2418' : '#ffffff'} !important;
            border-bottom: 1px solid ${isDark ? '#a68b5b' : '#d1d5db'} !important;
            color: ${isDark ? '#ffd700' : '#111827'} !important;
          }
        `}
      </style>
      <div className="pb-4 border-b border-secondary-200 dark:border-secondary-700">
        <h3 className="osrs-stat-label mb-4">Task Executions Over Time</h3>
        <div className="rounded p-4 bg-white dark:bg-secondary-800 border-2 border-secondary-200 dark:border-secondary-700">
          <Chart
            options={options}
            series={series}
            type="line"
            height={350}
          />
        </div>
      </div>
    </>
  );
};

