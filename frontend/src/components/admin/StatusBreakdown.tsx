import { Link } from 'react-router-dom';
import { STATUS_COLORS } from './utils';
import type { ExecutionSummary } from './types';

interface StatusBreakdownProps {
  executionSummary: ExecutionSummary;
}

export const StatusBreakdown: React.FC<StatusBreakdownProps> = ({ executionSummary }) => {
  return (
    <div>
      <h3 className="osrs-stat-label mb-3">Status Breakdown</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {Object.entries(executionSummary.statusBreakdown).map(([status, count]) => {
          const percentage = executionSummary.total > 0
            ? ((count / executionSummary.total) * 100).toFixed(1)
            : '0.0';
          return (
            <Link
              key={status}
              to={`/task-executions?status=${status}`}
              className="p-3 rounded hover:opacity-90 transition-opacity cursor-pointer block"
              style={{
                backgroundColor: `${STATUS_COLORS[status] || '#fff'}15`,
                border: `1px solid ${STATUS_COLORS[status] || '#fff'}40`,
                textDecoration: 'none'
              }}
            >
              <div className="flex items-center justify-between mb-1">
                <span
                  className="text-sm font-semibold capitalize"
                  style={{ color: STATUS_COLORS[status] || '#fff' }}
                >
                  {status}
                </span>
                <span className="text-xs osrs-text-secondary">{percentage}%</span>
              </div>
              <p className="text-lg font-bold" style={{ color: STATUS_COLORS[status] || '#fff' }}>
                {count.toLocaleString()}
              </p>
            </Link>
          );
        })}
      </div>
    </div>
  );
};

