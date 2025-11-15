interface AddPlayerFormProps {
  username: string;
  onUsernameChange: (username: string) => void;
  onAdd: () => void;
  adding: boolean;
}

export const AddPlayerForm: React.FC<AddPlayerFormProps> = ({
  username,
  onUsernameChange,
  onAdd,
  adding,
}) => {
  return (
    <div className="osrs-card">
      <h2 className="osrs-card-title text-lg sm:text-xl mb-4">Add New Player</h2>
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="text"
          placeholder="Enter username..."
          value={username}
          onChange={(e) => onUsernameChange(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              onAdd();
            }
          }}
          className="flex-1 input"
          maxLength={12}
        />
        <button
          onClick={onAdd}
          disabled={adding || !username.trim()}
          className="osrs-btn px-4 sm:px-6 w-full sm:w-auto"
        >
          {adding ? 'Adding...' : 'Add Player'}
        </button>
      </div>
    </div>
  );
};

