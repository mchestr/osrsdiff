interface IntervalEditorProps {
  value: string;
  onValueChange: (value: string) => void;
  onSave: () => void;
  onCancel: () => void;
}

export const IntervalEditor: React.FC<IntervalEditorProps> = ({
  value,
  onValueChange,
  onSave,
  onCancel,
}) => {
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      const interval = parseInt(value);
      if (interval >= 1 && interval <= 10080) {
        onSave();
      }
    } else if (e.key === 'Escape') {
      onCancel();
    }
  };

  return (
    <div className="flex items-center gap-1 sm:gap-2 flex-wrap">
      <input
        type="number"
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        className="input w-16 sm:w-20 text-xs sm:text-sm"
        min="1"
        max="10080"
        autoFocus
        onKeyPress={handleKeyPress}
      />
      <button
        onClick={() => {
          const interval = parseInt(value);
          if (interval >= 1 && interval <= 10080) {
            onSave();
          }
        }}
        className="osrs-btn text-xs px-1.5 sm:px-2 py-1"
      >
        Save
      </button>
      <button
        onClick={onCancel}
        className="osrs-btn text-xs px-1.5 sm:px-2 py-1"
      >
        Cancel
      </button>
    </div>
  );
};

