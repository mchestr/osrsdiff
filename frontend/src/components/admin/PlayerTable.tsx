import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import type { PlayerResponse } from '../../api/models/PlayerResponse';
import { DataTable, type Column } from '../common';
import { IntervalEditor } from './IntervalEditor';
import { PlayerActions } from './PlayerActions';
import { PlayerStatusBadge } from './PlayerStatusBadge';

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
  const columns: Column<PlayerResponse>[] = [
    {
      key: 'username',
      label: 'Username',
      sortable: true,
      render: (player) => (
        <Link
          to={`/players/${player.username}`}
          className="font-medium hover:text-primary-500 dark:hover:text-primary-400 transition-colors"
          onClick={(e) => e.stopPropagation()}
        >
          {player.username}
        </Link>
      ),
      className: 'whitespace-nowrap font-medium',
    },
    {
      key: 'is_active',
      label: 'Status',
      sortable: true,
      render: (player) => <PlayerStatusBadge isActive={player.is_active} />,
      className: 'whitespace-nowrap',
    },
    {
      key: 'created_at',
      label: 'Created',
      sortable: true,
      sortFn: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      render: (player) => (
        <span className="hidden sm:table-cell">
          {format(new Date(player.created_at), 'MMM d, yyyy')}
        </span>
      ),
      className: 'hidden sm:table-cell whitespace-nowrap',
      headerClassName: 'hidden sm:table-cell',
    },
    {
      key: 'last_fetched',
      label: 'Last Fetched',
      sortable: true,
      sortFn: (a, b) => {
        if (!a.last_fetched) return 1;
        if (!b.last_fetched) return -1;
        return new Date(a.last_fetched).getTime() - new Date(b.last_fetched).getTime();
      },
      render: (player) => (
        <span className="hidden md:table-cell">
          {player.last_fetched
            ? format(new Date(player.last_fetched), 'MMM d, HH:mm')
            : 'Never'}
        </span>
      ),
      className: 'hidden md:table-cell whitespace-nowrap',
      headerClassName: 'hidden md:table-cell',
    },
    {
      key: 'fetch_interval_minutes',
      label: 'Interval',
      sortable: true,
      render: (player) => {
        const isEditing = editingInterval === player.id;
        if (isEditing) {
          return (
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
          );
        }
        return (
          <span
            className="cursor-pointer hover:opacity-80 transition-opacity"
            onClick={(e) => {
              e.stopPropagation();
              onStartEditInterval(player.id, player.fetch_interval_minutes);
            }}
            title="Click to edit"
            onMouseEnter={(e) => {
              e.currentTarget.style.color = '#ffd700';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = '';
            }}
          >
            {player.fetch_interval_minutes} min
          </span>
        );
      },
      className: 'whitespace-nowrap',
    },
    {
      key: 'actions',
      label: 'Actions',
      sortable: false,
      render: (player) => (
        <PlayerActions
          player={player}
          onTriggerFetch={onTriggerFetch}
          onDeactivate={onDeactivate}
          onReactivate={onReactivate}
          onDelete={onDelete}
          activatingPlayer={activatingPlayer}
          deletingPlayer={deletingPlayer}
        />
      ),
      className: 'whitespace-nowrap',
    },
  ];

  return (
    <DataTable
      data={players}
      columns={columns}
      keyExtractor={(player) => player.id}
      emptyMessage="No players found"
      searchable={{
        placeholder: 'Search players...',
        searchKeys: ['username'],
        showClearButton: true,
      }}
      limitConfig={{
        value: 50,
        onChange: () => {
          // Limit selector for visual consistency - could be made functional later
        },
        options: [25, 50, 100, 200],
      }}
    />
  );
};

