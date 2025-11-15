import { ApexOptions } from 'apexcharts';
import { useMemo } from 'react';
import Chart from 'react-apexcharts';
import type { CostStatsResponse } from '../../api/models/OpenAICostStatsResponse';
import { useTheme } from '../../contexts/ThemeContext';
import { getChartColors } from '../../utils/chartColors';

interface CostStatisticsChartProps {
  costs: CostStatsResponse | null;
}

// Vibrant colors for dark theme
const COLORS_DARK = [
  '#ffd700', // Gold
  '#4caf50', // Green
  '#2196f3', // Blue
  '#ff9800', // Orange
  '#9c27b0', // Purple
  '#f44336', // Red
  '#00bcd4', // Cyan
  '#ffc107', // Amber
];

// Vibrant colors for light theme
const COLORS_LIGHT = [
  '#d4af37', // Gold
  '#4caf50', // Green
  '#2196f3', // Blue
  '#ff9800', // Orange
  '#9c27b0', // Purple
  '#f44336', // Red
  '#00bcd4', // Cyan
  '#ffc107', // Amber
];

export const CostStatisticsChart: React.FC<CostStatisticsChartProps> = ({ costs }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const colors = isDark ? COLORS_DARK : COLORS_LIGHT;
  const chartColors = getChartColors(theme);

  const timePeriodData = useMemo(() => {
    if (!costs) return [];

    return [
      {
        period: '24 Hours',
        cost: costs.cost_last_24h_usd,
      },
      {
        period: '7 Days',
        cost: costs.cost_last_7d_usd,
      },
      {
        period: '30 Days',
        cost: costs.cost_last_30d_usd,
      },
      {
        period: 'Total',
        cost: costs.total_cost_usd,
      },
    ];
  }, [costs]);

  const modelData = useMemo(() => {
    if (!costs || Object.keys(costs.by_model).length === 0) return [];

    return Object.entries(costs.by_model)
      .map(([model, stats]) => ({
        name: model,
        value: stats.cost_usd,
        count: stats.count,
      }))
      .sort((a, b) => b.value - a.value);
  }, [costs]);

  if (!costs) {
    return null;
  }

  const formatCurrency = (value: number) => `$${value.toFixed(4)}`;

  const timePeriodOptions: ApexOptions = useMemo(() => ({
    chart: {
      type: 'bar',
      fontFamily: 'Inter, sans-serif',
      height: 350,
      toolbar: {
        show: false,
      },
    },
    colors: colors,
    plotOptions: {
      bar: {
        borderRadius: 4,
        columnWidth: '60%',
      },
    },
    dataLabels: {
      enabled: false,
    },
    xaxis: {
      categories: timePeriodData.map((d) => d.period),
      labels: {
        style: {
          fontSize: '12px',
          colors: chartColors.xAxisLabels,
        },
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
        formatter: (value: number) => `$${value.toFixed(2)}`,
      },
    },
    grid: {
      borderColor: chartColors.gridBorder,
      strokeDashArray: 3,
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
    tooltip: {
      theme: chartColors.tooltipTheme,
      style: {
        fontSize: '12px',
        fontFamily: 'Inter, sans-serif',
      },
      y: {
        formatter: (value: number) => formatCurrency(value),
      },
    },
  }), [timePeriodData, chartColors, colors]);

  const timePeriodSeries = [
    {
      name: 'Cost',
      data: timePeriodData.map((d) => d.cost),
    },
  ];

  const pieOptions: ApexOptions = useMemo(() => ({
    chart: {
      type: 'pie',
      fontFamily: 'Inter, sans-serif',
      height: 350,
      toolbar: {
        show: false,
      },
    },
    colors: colors,
    labels: modelData.map((d) => d.name),
    legend: {
      position: 'bottom',
      fontSize: '11px',
      labels: {
        colors: chartColors.legendLabels,
      },
    },
    dataLabels: {
      enabled: false,
    },
    tooltip: {
      fillSeriesColor: false,
      theme: isDark ? 'dark' : 'light',
      style: {
        fontSize: '12px',
        fontFamily: 'Inter, sans-serif',
      },
      y: {
        formatter: (value: number) => {
          const total = modelData.reduce((sum, d) => sum + d.value, 0);
          const percentage = ((value / total) * 100).toFixed(1);
          return `${formatCurrency(value)} (${percentage}%)`;
        },
      },
    },
  }), [modelData, chartColors, colors, isDark]);

  const pieSeries = modelData.map((d) => d.value);

  // Reverse data for horizontal bar chart (top to bottom display)
  const reversedModelData = useMemo(() => [...modelData].reverse(), [modelData]);

  const horizontalBarOptions: ApexOptions = useMemo(() => ({
    chart: {
      type: 'bar',
      fontFamily: 'Inter, sans-serif',
      height: 350,
      toolbar: {
        show: false,
      },
    },
    colors: colors,
    plotOptions: {
      bar: {
        borderRadius: 4,
        horizontal: true,
      },
    },
    dataLabels: {
      enabled: false,
    },
    xaxis: {
      categories: reversedModelData.map((d) => d.name),
      labels: {
        style: {
          fontSize: '11px',
          colors: chartColors.yAxisLabels,
        },
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
          colors: chartColors.xAxisLabels,
        },
        formatter: (value: number) => {
          if (typeof value === 'number' && !isNaN(value)) {
            return `$${value.toFixed(2)}`;
          }
          return String(value);
        },
      },
    },
    grid: {
      borderColor: chartColors.gridBorder,
      strokeDashArray: 3,
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
    tooltip: {
      theme: chartColors.tooltipTheme,
      style: {
        fontSize: '12px',
        fontFamily: 'Inter, sans-serif',
      },
      custom: ({ series, seriesIndex, dataPointIndex }) => {
        const model = reversedModelData[dataPointIndex];
        const value = series[seriesIndex][dataPointIndex];
        return `
          <div style="padding: 8px;">
            <div style="font-weight: 600; margin-bottom: 4px;">${model.name}</div>
            <div>${formatCurrency(value)}</div>
            <div style="font-size: 11px; opacity: 0.8;">${model.count} summaries</div>
          </div>
        `;
      },
    },
  }), [reversedModelData, chartColors, colors]);

  const horizontalBarSeries = useMemo(() => [
    {
      name: 'Cost',
      data: reversedModelData.map((d) => d.value),
    },
  ], [reversedModelData]);

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
      <div className="space-y-6 pt-4 border-t border-secondary-200 dark:border-secondary-700">
      {/* Time Period Comparison */}
      <div>
        <h3 className="osrs-stat-label mb-4">Cost by Time Period</h3>
        <div className="rounded p-4 bg-white dark:bg-secondary-800 border-2 border-secondary-200 dark:border-secondary-700">
          <Chart
            options={timePeriodOptions}
            series={timePeriodSeries}
            type="bar"
            height={350}
          />
        </div>
      </div>

      {/* Model Breakdown */}
      {modelData.length > 0 && (
        <div>
          <h3 className="osrs-stat-label mb-4">Cost Breakdown by Model</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Pie Chart */}
            <div className="rounded p-4 bg-white dark:bg-secondary-800 border-2 border-secondary-200 dark:border-secondary-700">
              <Chart
                options={pieOptions}
                series={pieSeries}
                type="pie"
                height={350}
              />
            </div>

            {/* Horizontal Bar Chart */}
            <div className="rounded p-4 bg-white dark:bg-secondary-800 border-2 border-secondary-200 dark:border-secondary-700">
              <Chart
                options={horizontalBarOptions}
                series={horizontalBarSeries}
                type="bar"
                height={350}
              />
            </div>
          </div>
        </div>
      )}
      </div>
    </>
  );
};

