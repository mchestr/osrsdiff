import React from 'react';
import { TypedInput } from './TypedInput';
import type { Setting, SettingFormData } from './types';

interface SettingEditModalProps {
  setting: Setting;
  formData: SettingFormData;
  onValueChange: (value: string) => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
}

export const SettingEditModal: React.FC<SettingEditModalProps> = ({
  setting,
  formData,
  onValueChange,
  onSave,
  onCancel,
  saving,
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50" onClick={onCancel}>
      <div className="osrs-card max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold">{setting.display_name || setting.key}</h2>
          {setting.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">{setting.description}</p>
          )}
          <div className="mt-2">
            <span className="text-xs text-gray-500 dark:text-gray-500 font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
              {setting.key}
            </span>
          </div>
        </div>
        <div className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">Value</label>
            <TypedInput
              setting={setting}
              value={formData.value}
              onChange={onValueChange}
            />
          </div>
        </div>
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="osrs-btn px-4 py-2 bg-secondary-100 dark:bg-secondary-800 border border-secondary-300 dark:border-secondary-600 hover:bg-secondary-200 dark:hover:bg-secondary-700 text-secondary-900 dark:text-secondary-100"
            disabled={saving}
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={saving || !formData.value}
            className="osrs-btn px-4 py-2"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
};

