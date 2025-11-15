import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  fullScreen?: boolean;
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
};

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message,
  size = 'md',
  fullScreen = false,
}) => {
  const containerClasses = fullScreen
    ? 'flex items-center justify-center min-h-screen'
    : 'flex items-center justify-center py-12';

  return (
    <div className={containerClasses}>
      <div className="flex flex-col items-center gap-4">
        <div
          className={`${sizeClasses[size]} border-4 border-secondary-200 dark:border-secondary-700 border-t-primary-600 dark:border-t-primary-400 rounded-full animate-spin`}
        />
        {message && (
          <div className="text-secondary-600 dark:text-secondary-400 text-xl">{message}</div>
        )}
      </div>
    </div>
  );
};

