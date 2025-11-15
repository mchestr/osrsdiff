import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import type { PlayerResponse } from '../../api/models/PlayerResponse';
import { IntervalEditor } from './IntervalEditor';
import { PlayerActions } from './PlayerActions';
import { PlayerStatusBadge } from './PlayerStatusBadge';

interface PlayerTableRowProps {
  player: PlayerResponse;
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

export const PlayerTableRow: React.FC<PlayerTableRowProps> = ({
  player,
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
  const isEditing = editingInterval === player.id;

  return (
    <tr
      style={{ borderBottom: '1px solid #8b7355' }}
      className="hover:opacity-80"
    >
      <td className="px-3 sm:px-4 md:px-6 py-3 sm:py-4 whitespace-nowrap font-medium">
        <Link
          to={`/players/${player.username}`}
          className="osrs-text text-sm sm:text-base hover:text-primary-500 dark:hover:text-primary-400 transition-colors"
        >
          {player.username}
        </Link>
      </td>
      <td className="px-3 sm:px-4 md:px-6 py-3 sm:py-4 whitespace-nowrap">
        <PlayerStatusBadge isActive={player.is_active} />
      </td>
      <td className="px-3 sm:px-4 md:px-6 py-3 sm:py-4 whitespace-nowrap text-xs sm:text-sm osrs-text-secondary hidden sm:table-cell">
        {format(new Date(player.created_at), 'MMM d, yyyy')}
      </td>
      <td className="px-3 sm:px-4 md:px-6 py-3 sm:py-4 whitespace-nowrap text-xs sm:text-sm osrs-text-secondary hidden md:table-cell">
        {player.last_fetched
          ? format(new Date(player.last_fetched), 'MMM d, HH:mm')
          : 'Never'}
      </td>
      <td className="px-3 sm:px-4 md:px-6 py-3 sm:py-4 whitespace-nowrap">
        {isEditing ? (
          <IntervalEditor
            value={intervalValue}
            onValueChange={onIntervalValueChange}
            onSave={() => {
              const interval = parseInt(intervalValue);
              if (interval >= 1 && interval <= 10080) {
                onSaveInterval(player.username, interval);
              }
            }}
            onCancel={onCancelEditInterval}
          />
        ) : (
          <span
            className="text-xs sm:text-sm osrs-text-secondary cursor-pointer hover:opacity-80 transition-opacity"
            onClick={() => onStartEditInterval(player.id, player.fetch_interval_minutes)}
            title="Click to edit"
            style={{ color: 'inherit' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = '#ffd700';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = '';
            }}
          >
            {player.fetch_interval_minutes} min
          </span>
        )}
      </td>
      <td className="px-3 sm:px-4 md:px-6 py-3 sm:py-4 whitespace-nowrap">
        <PlayerActions
          player={player}
          onTriggerFetch={onTriggerFetch}
          onDeactivate={onDeactivate}
          onReactivate={onReactivate}
          onDelete={onDelete}
          activatingPlayer={activatingPlayer}
          deletingPlayer={deletingPlayer}
        />
      </td>
    </tr>
  );
};

