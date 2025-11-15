interface PlayerSearchBarProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
}

export const PlayerSearchBar: React.FC<PlayerSearchBarProps> = ({
  searchTerm,
  onSearchChange,
}) => {
  return (
    <div className="flex gap-2 sm:gap-4">
      <input
        type="text"
        placeholder="Search players..."
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
        className="flex-1 input"
      />
    </div>
  );
};

