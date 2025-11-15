import { ApexOptions } from 'apexcharts';
import Chart from 'react-apexcharts';
import type { ProgressAnalysisResponse } from '../../api/models/ProgressAnalysisResponse';
import { useTheme } from '../../hooks';
import { getChartColors, getXAxisLabelColors } from '../../utils/chartColors';

interface TopSkillsChartProps {
  progressWeek: ProgressAnalysisResponse | null;
}

export const TopSkillsChart: React.FC<TopSkillsChartProps> = ({ progressWeek }) => {
  const { theme } = useTheme();
  const colors = getChartColors(theme);
  const topSkillsData = progressWeek
    ? Object.entries(progressWeek.progress.experience_gained)
        .filter(([skill]) => skill !== 'overall')
        .map(([skill, exp]) => ({
          name: skill.charAt(0).toUpperCase() + skill.slice(1),
          value: exp,
        }))
        .filter((item) => item.value > 0)
        .sort((a, b) => b.value - a.value)
        .slice(0, 10)
    : [];

  if (topSkillsData.length === 0) {
    return (
      <div>
        <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">
          Top Skills XP Gained (7d)
        </h3>
        <div className="text-center py-8 text-secondary-500 dark:text-secondary-300">
          No progress data available
        </div>
      </div>
    );
  }

  const categories = topSkillsData.map((item) => item.name);
  const data = topSkillsData.map((item) => item.value);

  const options: ApexOptions = {
    legend: {
      show: false,
    },
    colors: [colors.primary],
    chart: {
      fontFamily: 'Inter, sans-serif',
      height: 350,
      type: 'bar',
      toolbar: {
        show: false,
      },
    },
    plotOptions: {
      bar: {
        borderRadius: 8,
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
      borderColor: colors.gridBorder,
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
      name: 'XP Gained',
      data,
    },
  ];

  return (
    <div>
      <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">
        Top Skills XP Gained (7d)
      </h3>
      <div className="w-full">
        <Chart key={theme} options={options} series={series} type="bar" height={350} />
      </div>
    </div>
  );
};

