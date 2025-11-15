const LIMIT_OPTIONS = [25, 50, 100, 200] as const;

interface TaskExecutionSearchBarProps {
  searchInput: string;
  onSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onResetSearch: () => void;
  limit: number;
  onLimitChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  isFiltering?: boolean;
}

export const TaskExecutionSearchBar: React.FC<TaskExecutionSearchBarProps> = ({
  searchInput,
  onSearchChange,
  onResetSearch,
  limit,
  onLimitChange,
  isFiltering = false,
}) => {
  return (
    <div className="osrs-card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="osrs-card-title">Search</h2>
        {isFiltering && <div className="osrs-text-secondary text-sm">Filtering...</div>}
      </div>
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <input
            type="text"
            value={searchInput}
            onChange={onSearchChange}
            placeholder="Search by task name, status, schedule ID, or player name..."
            className="input w-full"
          />
        </div>
        <button onClick={onResetSearch} className="osrs-btn">
          Clear
        </button>
        <div className="flex items-center gap-2">
          <label className="text-sm osrs-text-secondary">Limit:</label>
          <select value={limit} onChange={onLimitChange} className="input">
            {LIMIT_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};

