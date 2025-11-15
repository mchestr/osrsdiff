/**
 * Format large numbers with appropriate suffixes (K, M)
 */
export const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
};

/**
 * Format numbers with locale-specific formatting
 */
export const formatNumberLocale = (num: number): string => {
  return num.toLocaleString();
};

/**
 * Format currency values
 */
export const formatCurrency = (value: number, decimals = 4): string => {
  return `$${value.toFixed(decimals)}`;
};

/**
 * Format XP values with appropriate suffixes
 */
export const formatXP = (value: number): string => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(2)}M XP`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K XP`;
  }
  return `${value} XP`;
};

