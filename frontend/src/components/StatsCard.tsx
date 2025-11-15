import React from 'react';

export interface StatsCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  color?: 'primary' | 'blue' | 'success' | 'purple' | 'orange' | 'red';
  loading?: boolean;
  trend?: {
    value: number;
    label: string;
  };
}

const colorClasses = {
  primary: {
    bg: 'bg-gradient-to-br from-primary-50/50 to-primary-100/50 dark:from-primary-900/10 dark:to-primary-800/10',
    border: 'border-primary-200 dark:border-primary-700/50',
    text: 'text-primary-600 dark:text-primary-400',
    iconBg: 'bg-primary-500',
  },
  blue: {
    bg: 'bg-gradient-to-br from-blue-50/50 to-blue-100/50 dark:from-blue-900/10 dark:to-blue-800/10',
    border: 'border-blue-200 dark:border-blue-700/50',
    text: 'text-blue-600 dark:text-blue-400',
    iconBg: 'bg-blue-500',
  },
  success: {
    bg: 'bg-gradient-to-br from-green-50/50 to-green-100/50 dark:from-green-900/10 dark:to-green-800/10',
    border: 'border-green-200 dark:border-green-700/50',
    text: 'text-green-600 dark:text-green-400',
    iconBg: 'bg-green-500',
  },
  purple: {
    bg: 'bg-gradient-to-br from-purple-50/50 to-purple-100/50 dark:from-purple-900/10 dark:to-purple-800/10',
    border: 'border-purple-200 dark:border-purple-700/50',
    text: 'text-purple-600 dark:text-purple-400',
    iconBg: 'bg-purple-500',
  },
  orange: {
    bg: 'bg-gradient-to-br from-orange-50/50 to-orange-100/50 dark:from-orange-900/10 dark:to-orange-800/10',
    border: 'border-orange-200 dark:border-orange-700/50',
    text: 'text-orange-600 dark:text-orange-400',
    iconBg: 'bg-orange-500',
  },
  red: {
    bg: 'bg-gradient-to-br from-red-50/50 to-red-100/50 dark:from-red-900/10 dark:to-red-800/10',
    border: 'border-red-200 dark:border-red-700/50',
    text: 'text-red-600 dark:text-red-400',
    iconBg: 'bg-red-500',
  },
};

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  icon,
  color = 'primary',
  loading = false,
  trend,
}) => {
  const colors = colorClasses[color];

  if (loading) {
    return (
      <div className={`p-6 rounded-xl border ${colors.bg} ${colors.border} transition-all duration-200 bg-white dark:bg-gray-800`}>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20 mb-3 animate-pulse"></div>
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-24 animate-pulse"></div>
          </div>
          {icon && (
            <div className={`w-12 h-12 rounded-lg ${colors.iconBg} opacity-20 animate-pulse`}></div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`p-6 rounded-xl border ${colors.bg} ${colors.border} hover:shadow-lg transition-all duration-200 group bg-white dark:bg-gray-800`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2 uppercase tracking-wide">
            {title}
          </p>
          <p className={`text-3xl font-bold ${colors.text} mb-1`}>
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
          {trend && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 flex items-center">
              <span className={`${trend.value >= 0 ? 'text-green-600' : 'text-red-600'} font-medium`}>
                {trend.value > 0 ? '+' : ''}
                {trend.value}%
              </span>
              <span className="ml-1">{trend.label}</span>
            </p>
          )}
        </div>
        {icon && (
          <div className={`w-12 h-12 rounded-lg ${colors.iconBg} flex items-center justify-center text-white shadow-md group-hover:scale-110 transition-transform duration-200 flex-shrink-0 ml-4`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
};

