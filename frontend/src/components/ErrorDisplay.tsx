import React from 'react';

interface ErrorDisplayProps {
  error: string;
  onRetry?: () => void;
  retryLabel?: string;
}

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  onRetry,
  retryLabel = 'Retry',
}) => {
  return (
    <div className="osrs-card">
      <div className="flex flex-col items-center gap-4 py-8">
        <div className="text-red-600 dark:text-red-400 text-center">{error}</div>
        {onRetry && (
          <button onClick={onRetry} className="osrs-btn">
            {retryLabel}
          </button>
        )}
      </div>
    </div>
  );
};

