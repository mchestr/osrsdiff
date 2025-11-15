import React from 'react';
import type { Setting } from './types';

interface SettingActionButtonsProps {
  setting: Setting;
  onEdit: (setting: Setting) => void;
  onReset: (key: string) => void;
  disabled?: boolean;
}

export const SettingActionButtons: React.FC<SettingActionButtonsProps> = ({
  setting,
  onEdit,
  onReset,
  disabled = false,
}) => {
  return (
    <div className="md:col-span-1 flex gap-2 justify-end" onClick={(e) => e.stopPropagation()}>
      <button
        onClick={() => onEdit(setting)}
        className="osrs-btn px-3 py-2 bg-secondary-100 dark:bg-secondary-800 border border-secondary-300 dark:border-secondary-600 hover:bg-secondary-200 dark:hover:bg-secondary-700 text-secondary-900 dark:text-secondary-100 rounded transition-colors"
        disabled={disabled}
        title="Edit"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
          />
        </svg>
      </button>
      <button
        onClick={() => onReset(setting.key)}
        className="osrs-btn px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white border-blue-600 rounded transition-colors"
        disabled={disabled}
        title="Reset to default"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      </button>
    </div>
  );
};

