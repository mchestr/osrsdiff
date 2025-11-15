// Helper function to format large numbers
export const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
};

export const STATUS_COLORS: Record<string, string> = {
  success: '#4caf50',
  failure: '#d32f2f',
  retry: '#ff9800',
  pending: '#2196f3',
  running: '#9c27b0',
  cancelled: '#9e9e9e',
  skipped: '#9e9e9e',
  warning: '#ff9800',
  timeout: '#f44336',
};

