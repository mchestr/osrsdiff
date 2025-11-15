import React from 'react';
import { StatsCard, StatsCardProps } from './StatsCard';

export interface StatsGridProps {
  stats: StatsCardProps[];
  loading?: boolean;
  columns?: 2 | 3 | 4;
}

export const StatsGrid: React.FC<StatsGridProps> = ({
  stats,
  loading = false,
  columns = 4,
}) => {
  const gridCols = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-2 md:grid-cols-4',
  };

  if (loading) {
    return (
      <div className={`grid ${gridCols[columns]} gap-4 lg:gap-6`}>
        {[1, 2, 3, 4].slice(0, columns).map((i) => (
          <StatsCard
            key={i}
            title="Loading..."
            value={0}
            loading={true}
          />
        ))}
      </div>
    );
  }

  return (
    <div className={`grid ${gridCols[columns]} gap-4 lg:gap-6`}>
      {stats.map((stat, index) => (
        <StatsCard key={index} {...stat} />
      ))}
    </div>
  );
};

