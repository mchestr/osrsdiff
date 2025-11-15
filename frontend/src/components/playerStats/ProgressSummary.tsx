import { format } from 'date-fns';
import type { PlayerSummary } from '../../types/player';

interface ProgressSummaryProps {
  summary: PlayerSummary;
}

export const ProgressSummary: React.FC<ProgressSummaryProps> = ({ summary }) => {
  return (
    <div className="card bg-gradient-to-br from-primary-50 to-primary-100 dark:bg-secondary-800 dark:from-secondary-800 dark:to-secondary-800 border-2 border-primary-200 dark:border-secondary-700 shadow-sm">
      <div className="flex items-start gap-4">
        <div className="text-3xl flex-shrink-0">✨</div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100">
              Progress Analysis
            </h3>
            <span className="text-sm text-secondary-600 dark:text-secondary-200 font-medium">
              {format(new Date(summary.generated_at), 'MMM d')}
            </span>
          </div>
          {summary.summary && (
            <p className="text-secondary-800 dark:text-secondary-200 mb-4 leading-relaxed">
              {summary.summary}
            </p>
          )}
          {summary.summary_points && summary.summary_points.length > 0 ? (
            <ul className="space-y-2 mb-4">
              {summary.summary_points.map((point, index) => (
                <li key={index} className="text-secondary-800 dark:text-secondary-200 flex items-start leading-relaxed">
                  <span className="w-2 h-2 rounded-full bg-primary-600 dark:bg-primary-400 mr-3 mt-2 flex-shrink-0" />
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-secondary-800 dark:text-secondary-200 mb-4 leading-relaxed">
              {summary.summary_text}
            </p>
          )}
          <div className="pt-3 border-t border-primary-200 dark:border-secondary-700">
            <p className="text-sm text-secondary-600 dark:text-secondary-200 font-medium">
              {format(new Date(summary.period_start), 'MMM d')} - {format(new Date(summary.period_end), 'MMM d, yyyy')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

