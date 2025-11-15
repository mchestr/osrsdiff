import type { CostStatsResponse } from '../../api/models/OpenAICostStatsResponse';
import { CostStatisticsChart } from './CostStatisticsChart';
import { formatNumber } from './utils';

interface CostStatisticsProps {
  costs: CostStatsResponse | null;
  loading: boolean;
}

export const CostStatistics: React.FC<CostStatisticsProps> = ({ costs, loading }) => {
  if (loading) {
    return (
      <div className="osrs-card">
        <h2 className="osrs-card-title mb-3 sm:mb-4 text-lg sm:text-xl">Cost Statistics</h2>
        <div className="flex items-center justify-center py-4">
          <div className="osrs-text-secondary">Loading cost statistics...</div>
        </div>
      </div>
    );
  }

  if (!costs) {
    return (
      <div className="osrs-card">
        <h2 className="osrs-card-title mb-3 sm:mb-4 text-lg sm:text-xl">Cost Statistics</h2>
        <div className="flex items-center justify-center py-4">
          <div className="osrs-text-secondary">No cost data available</div>
        </div>
      </div>
    );
  }

  return (
    <div className="osrs-card">
      <h2 className="osrs-card-title mb-3 sm:mb-4 text-lg sm:text-xl">Cost Statistics</h2>
      <div className="space-y-4">
        {/* Cost Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="osrs-card hover:shadow-card-hover transition-shadow">
            <h3 className="osrs-stat-label mb-2">Total Cost</h3>
            <p className="osrs-stat-value text-2xl">
              ${costs.total_cost_usd.toFixed(4)}
            </p>
          </div>
          <div className="osrs-card hover:shadow-card-hover transition-shadow">
            <h3 className="osrs-stat-label mb-2">Last 24 Hours</h3>
            <p className="osrs-stat-value text-2xl text-success-600">
              ${costs.cost_last_24h_usd.toFixed(4)}
            </p>
          </div>
          <div className="osrs-card hover:shadow-card-hover transition-shadow">
            <h3 className="osrs-stat-label mb-2">Last 7 Days</h3>
            <p className="osrs-stat-value text-2xl text-success-600">
              ${costs.cost_last_7d_usd.toFixed(4)}
            </p>
          </div>
          <div className="osrs-card hover:shadow-card-hover transition-shadow">
            <h3 className="osrs-stat-label mb-2">Last 30 Days</h3>
            <p className="osrs-stat-value text-2xl text-success-600">
              ${costs.cost_last_30d_usd.toFixed(4)}
            </p>
          </div>
        </div>

        {/* Token Usage Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-secondary-200 dark:border-secondary-700">
          <div>
            <h3 className="osrs-stat-label mb-1">Total Summaries</h3>
            <p className="osrs-stat-value">{costs.total_summaries.toLocaleString()}</p>
          </div>
          <div>
            <h3 className="osrs-stat-label mb-1">Total Tokens</h3>
            <p className="osrs-stat-value">{formatNumber(costs.total_tokens)}</p>
            <p className="text-xs osrs-text-secondary mt-1">
              {formatNumber(costs.total_prompt_tokens)} prompt + {formatNumber(costs.total_completion_tokens)} completion
            </p>
          </div>
          <div>
            <h3 className="osrs-stat-label mb-1">Avg Cost per Summary</h3>
            <p className="osrs-stat-value">
              {costs.total_summaries > 0
                ? `$${(costs.total_cost_usd / costs.total_summaries).toFixed(6)}`
                : '$0.000000'}
            </p>
          </div>
        </div>

        {/* Model Breakdown */}
        {Object.keys(costs.by_model).length > 0 && (
          <div className="pt-2 border-t border-secondary-200 dark:border-secondary-700">
            <h3 className="osrs-stat-label mb-3">Cost Breakdown by Model</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(costs.by_model).map(([model, stats]) => (
                <div
                  key={model}
                  className="p-3 rounded bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-700 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold osrs-text text-primary-600 dark:text-primary-400">
                      {model}
                    </span>
                    <span className="text-sm osrs-text-secondary">
                      {stats.count} summaries
                    </span>
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="osrs-text-secondary">Cost:</span>
                      <span className="osrs-text text-success-600 dark:text-success-400 font-medium">
                        ${stats.cost_usd.toFixed(4)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="osrs-text-secondary">Tokens:</span>
                      <span className="osrs-text font-medium">{formatNumber(stats.total_tokens)}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="osrs-text-secondary">Avg per summary:</span>
                      <span className="osrs-text-secondary">
                        ${stats.count > 0 ? (stats.cost_usd / stats.count).toFixed(6) : '0.000000'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cost Charts */}
        <CostStatisticsChart costs={costs} />
      </div>
    </div>
  );
};

