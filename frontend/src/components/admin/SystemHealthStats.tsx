import { formatNumber } from './utils';
import type { DatabaseStats, SystemHealth } from './types';

interface SystemHealthStatsProps {
  health: SystemHealth | null;
  stats: DatabaseStats | null;
}

export const SystemHealthStats: React.FC<SystemHealthStatsProps> = ({ health, stats }) => {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-7 gap-3 sm:gap-4 md:gap-6">
      {health && (
        <>
          <div className="osrs-card flex flex-col hover:shadow-card-hover transition-shadow">
            <h3 className="osrs-stat-label mb-2" style={{ minHeight: '2.5rem' }}>System Status</h3>
            <div className="flex items-center justify-center flex-1">
              <span
                className="text-4xl"
                style={{ color: health.status === 'healthy' ? '#22c55e' : '#ef4444' }}
                title={health.status.toUpperCase()}
              >
                {health.status === 'healthy' ? '✓' : '✗'}
              </span>
            </div>
          </div>
          <div className="osrs-card flex flex-col hover:shadow-card-hover transition-shadow">
            <h3 className="osrs-stat-label mb-2" style={{ minHeight: '2.5rem' }}>Database</h3>
            <div className="flex items-center justify-center flex-1">
              <span
                className="text-4xl"
                style={{ color: health.database_connected ? '#22c55e' : '#ef4444' }}
                title={health.database_connected ? 'Connected' : 'Disconnected'}
              >
                {health.database_connected ? '✓' : '✗'}
              </span>
            </div>
          </div>
          {health.total_storage_mb && (
            <div className="osrs-card flex flex-col">
              <h3 className="osrs-stat-label mb-2" style={{ minHeight: '2.5rem' }}>Storage</h3>
              <p className="osrs-stat-value flex-1 flex items-center" title={`${health.total_storage_mb.toFixed(2)} MB`}>
                {formatNumber(Math.round(health.total_storage_mb))} MB
              </p>
            </div>
          )}
        </>
      )}
      {stats && (
        <>
          <div className="osrs-card flex flex-col hover:shadow-card-hover transition-shadow">
            <h3 className="osrs-stat-label mb-2" style={{ minHeight: '2.5rem' }}>Total Players</h3>
            <p className="osrs-stat-value flex-1 flex items-center" title={stats.total_players.toString()}>
              {formatNumber(stats.total_players)}
            </p>
          </div>
          <div className="osrs-card flex flex-col hover:shadow-card-hover transition-shadow">
            <h3 className="osrs-stat-label mb-2" style={{ minHeight: '2.5rem' }}>Active Players</h3>
            <p className="osrs-stat-value flex-1 flex items-center text-success-600" title={stats.active_players.toString()}>
              {formatNumber(stats.active_players)}
            </p>
          </div>
          <div className="osrs-card flex flex-col hover:shadow-card-hover transition-shadow">
            <h3 className="osrs-stat-label mb-2" style={{ minHeight: '2.5rem' }}>Total Records</h3>
            <p className="osrs-stat-value flex-1 flex items-center" title={stats.total_hiscore_records.toLocaleString()}>
              {formatNumber(stats.total_hiscore_records)}
            </p>
          </div>
          <div className="osrs-card flex flex-col hover:shadow-card-hover transition-shadow">
            <h3 className="osrs-stat-label mb-2" style={{ minHeight: '2.5rem' }}>Records (24h)</h3>
            <p className="osrs-stat-value flex-1 flex items-center" title={stats.records_last_24h.toString()}>
              {formatNumber(stats.records_last_24h)}
            </p>
          </div>
        </>
      )}
    </div>
  );
};

