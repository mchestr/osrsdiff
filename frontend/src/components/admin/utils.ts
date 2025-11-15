// Re-export formatNumber from shared utils for backward compatibility
export { formatNumber } from '../../utils/formatters';

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

