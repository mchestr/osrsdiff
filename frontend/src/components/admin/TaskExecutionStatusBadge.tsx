import { STATUS_COLORS } from './utils';

interface TaskExecutionStatusBadgeProps {
  status: string;
}

export const TaskExecutionStatusBadge: React.FC<TaskExecutionStatusBadgeProps> = ({ status }) => {
  const color = STATUS_COLORS[status] || '#fff';
  return (
    <span
      className="px-2 inline-flex text-xs leading-5 font-semibold rounded"
      style={{
        backgroundColor: `${color}20`,
        border: `1px solid ${color}`,
        color: color,
      }}
    >
      {status}
    </span>
  );
};

