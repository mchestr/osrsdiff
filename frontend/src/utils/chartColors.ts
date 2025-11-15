/**
 * Centralized chart color definitions for consistent theming
 */

export const getChartColors = (theme: 'light' | 'dark') => {
  return {
    // Axis labels
    xAxisLabels: theme === 'dark' ? '#D1D5DB' : '#9CA3AF', // gray-300 : gray-400
    yAxisLabels: theme === 'dark' ? '#9CA3AF' : '#6B7280', // gray-400 : gray-500
    axisTitle: theme === 'dark' ? '#9CA3AF' : '#6B7280', // gray-400 : gray-500

    // Legend labels
    legendLabels: theme === 'dark' ? '#D1D5DB' : '#374151', // gray-300 : gray-700

    // Grid lines
    gridBorder: theme === 'dark' ? '#374151' : '#F3F4F6', // gray-700 : gray-100

    // Tooltip
    tooltipTheme: theme === 'dark' ? 'dark' : 'light',

    // Chart series colors
    primary: '#3b82f6', // blue-500
    secondary: '#10b981', // green-500
  };
};

/**
 * Generate an array of colors for all x-axis labels
 */
export const getXAxisLabelColors = (count: number, theme: 'light' | 'dark'): string[] => {
  const color = getChartColors(theme).xAxisLabels;
  return Array(count).fill(color);
};

/**
 * Generate an array of colors for all y-axis labels
 */
export const getYAxisLabelColors = (count: number, theme: 'light' | 'dark'): string[] => {
  const color = getChartColors(theme).yAxisLabels;
  return Array(count).fill(color);
};

