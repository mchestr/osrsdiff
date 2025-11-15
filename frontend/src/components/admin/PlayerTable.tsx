import type { PlayerResponse } from '../../api/models/PlayerResponse';
import { PlayerTableRow } from './PlayerTableRow';

interface PlayerTableProps {
  players: PlayerResponse[];
  editingInterval: number | null;
  intervalValue: string;
  onIntervalValueChange: (value: string) => void;
  onStartEditInterval: (playerId: number, currentInterval: number) => void;
  onSaveInterval: (username: string, interval: number) => void;
  onCancelEditInterval: () => void;
  onTriggerFetch: (username: string) => void;
  onDeactivate: (username: string) => void;
  onReactivate: (username: string) => void;
  onDelete: (username: string) => void;
  activatingPlayer: string | null;
  deletingPlayer: string | null;
}

export const PlayerTable: React.FC<PlayerTableProps> = ({
  players,
  editingInterval,
  intervalValue,
  onIntervalValueChange,
  onStartEditInterval,
  onSaveInterval,
  onCancelEditInterval,
  onTriggerFetch,
  onDeactivate,
  onReactivate,
  onDelete,
  activatingPlayer,
  deletingPlayer,
}) => {
  if (players.length === 0) {
    return (
      <div className="osrs-card text-center py-12">
        <p className="osrs-text-secondary">No players found.</p>
      </div>
    );
  }

  return (
    <div className="osrs-card">
      <div className="overflow-x-auto -mx-3 sm:mx-0">
        <div className="inline-block min-w-full align-middle">
          <div className="overflow-x-auto">
            <table className="min-w-full" style={{ borderCollapse: 'separate', borderSpacing: 0 }}>
              <thead>
                <tr className="bg-secondary-200 dark:bg-secondary-800">
                  <th className="px-3 sm:px-4 md:px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase whitespace-nowrap border-b-2 border-secondary-700 dark:border-secondary-600">
                    Username
                  </th>
                  <th className="px-3 sm:px-4 md:px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase whitespace-nowrap border-b-2 border-secondary-700 dark:border-secondary-600">
                    Status
                  </th>
                  <th className="px-3 sm:px-4 md:px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase whitespace-nowrap hidden sm:table-cell border-b-2 border-secondary-700 dark:border-secondary-600">
                    Created
                  </th>
                  <th className="px-3 sm:px-4 md:px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase whitespace-nowrap hidden md:table-cell border-b-2 border-secondary-700 dark:border-secondary-600">
                    Last Fetched
                  </th>
                  <th className="px-3 sm:px-4 md:px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase whitespace-nowrap border-b-2 border-secondary-700 dark:border-secondary-600">
                    Interval
                  </th>
                  <th className="px-3 sm:px-4 md:px-6 py-3 text-left text-xs font-medium osrs-text-secondary uppercase whitespace-nowrap border-b-2 border-secondary-700 dark:border-secondary-600">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {players.map((player) => (
                  <PlayerTableRow
                    key={player.id}
                    player={player}
                    editingInterval={editingInterval}
                    intervalValue={intervalValue}
                    onIntervalValueChange={onIntervalValueChange}
                    onStartEditInterval={onStartEditInterval}
                    onSaveInterval={onSaveInterval}
                    onCancelEditInterval={onCancelEditInterval}
                    onTriggerFetch={onTriggerFetch}
                    onDeactivate={onDeactivate}
                    onReactivate={onReactivate}
                    onDelete={onDelete}
                    activatingPlayer={activatingPlayer}
                    deletingPlayer={deletingPlayer}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div className="mt-4 text-sm osrs-text-secondary text-center">
        Showing {players.length} player{players.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
};

