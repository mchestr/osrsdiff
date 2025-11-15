interface PlayerStatusBadgeProps {
  isActive: boolean;
}

export const PlayerStatusBadge: React.FC<PlayerStatusBadgeProps> = ({ isActive }) => {
  return (
    <span
      className="px-2 inline-flex text-xs leading-5 font-semibold rounded"
      style={{
        backgroundColor: isActive ? 'rgba(255, 215, 0, 0.2)' : 'rgba(139, 115, 85, 0.2)',
        border: `1px solid ${isActive ? '#ffd700' : '#8b7355'}`,
        color: isActive ? '#ffd700' : '#8b7355'
      }}
    >
      {isActive ? 'Active' : 'Inactive'}
    </span>
  );
};

