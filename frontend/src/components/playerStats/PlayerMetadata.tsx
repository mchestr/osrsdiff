import { format } from 'date-fns';
import { useState } from 'react';
import type { PlayerMetadataResponse } from '../../api/models/PlayerMetadataResponse';

interface PlayerMetadataProps {
  metadata: PlayerMetadataResponse;
}

export const PlayerMetadata: React.FC<PlayerMetadataProps> = ({ metadata }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="card bg-white dark:bg-gray-800">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex justify-between items-center text-left"
      >
        <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100">Player Information</h2>
        <span className="text-secondary-600 dark:text-secondary-200 text-xl">
          {expanded ? '−' : '+'}
        </span>
      </button>
      {expanded && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
            <div>
              <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Status</h3>
              <p>
                <span
                  className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold ${
                    metadata.is_active
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-400'
                      : 'bg-gray-100 text-gray-800 dark:bg-secondary-700 dark:text-secondary-200'
                  }`}
                >
                  {metadata.is_active ? 'Active' : 'Inactive'}
                </span>
              </p>
            </div>
            <div>
              <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Fetch Interval</h3>
              <p className="text-secondary-900 dark:text-secondary-100">
                {metadata.fetch_interval_minutes} minutes
                {metadata.fetch_interval_minutes >= 60 && (
                  <span className="text-secondary-500 dark:text-secondary-300 ml-1">
                    ({Math.round(metadata.fetch_interval_minutes / 60 * 10) / 10} hours)
                  </span>
                )}
              </p>
            </div>
            <div>
              <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Total Records</h3>
              <p className="text-secondary-900 dark:text-secondary-100">
                {metadata.total_records.toLocaleString()}
              </p>
            </div>
            <div>
              <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Created</h3>
              <p className="text-secondary-900 dark:text-secondary-100">
                {format(new Date(metadata.created_at), 'MMM d, yyyy')}
              </p>
            </div>
            <div>
              <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Last Fetched</h3>
              <p className="text-secondary-900 dark:text-secondary-100">
                {metadata.last_fetched
                  ? format(new Date(metadata.last_fetched), 'MMM d, yyyy HH:mm')
                  : 'Never'}
              </p>
            </div>
            {metadata.avg_fetch_frequency_hours && (
              <div>
                <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Avg Fetch Frequency</h3>
                <p className="text-secondary-900 dark:text-secondary-100">
                  {Math.round(metadata.avg_fetch_frequency_hours * 10) / 10} hours
                </p>
              </div>
            )}
            {metadata.first_record && (
              <div>
                <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">First Record</h3>
                <p className="text-secondary-900 dark:text-secondary-100">
                  {format(new Date(metadata.first_record), 'MMM d, yyyy')}
                </p>
              </div>
            )}
            {metadata.latest_record && (
              <div>
                <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Latest Record</h3>
                <p className="text-secondary-900 dark:text-secondary-100">
                  {format(new Date(metadata.latest_record), 'MMM d, yyyy HH:mm')}
                </p>
              </div>
            )}
            <div>
              <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Records (24h)</h3>
              <p className="text-secondary-900 dark:text-secondary-100">
                {metadata.records_last_24h}
              </p>
            </div>
            <div>
              <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Records (7d)</h3>
              <p className="text-secondary-900 dark:text-secondary-100">
                {metadata.records_last_7d}
              </p>
            </div>
            {metadata.schedule_id && (
              <div>
                <h3 className="text-xs font-medium text-secondary-500 dark:text-secondary-300 mb-1 uppercase tracking-wide">Schedule ID</h3>
                <p className="text-secondary-500 dark:text-secondary-300 text-xs font-mono break-all">
                  {metadata.schedule_id}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

