import React from 'react';
import type { SettingFormData } from './types';

interface SettingCreateFormProps {
  formData: SettingFormData;
  onFormDataChange: (data: Partial<SettingFormData>) => void;
  onCreate: () => void;
  onCancel: () => void;
  saving: boolean;
}

export const SettingCreateForm: React.FC<SettingCreateFormProps> = ({
  formData,
  onFormDataChange,
  onCreate,
  onCancel,
  saving,
}) => {
  return (
    <div className="osrs-card p-4 border-2 border-primary-500 dark:border-primary-400">
      <h2 className="text-lg font-semibold mb-3">Create New Setting</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium mb-1 text-gray-600 dark:text-gray-400">Key</label>
          <input
            type="text"
            value={formData.key}
            onChange={(e) => onFormDataChange({ key: e.target.value })}
            className="input w-full py-1.5 text-sm"
            placeholder="e.g., openai_api_key"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1 text-gray-600 dark:text-gray-400">Display Name</label>
          <input
            type="text"
            value={formData.display_name}
            onChange={(e) => onFormDataChange({ display_name: e.target.value })}
            className="input w-full py-1.5 text-sm"
            placeholder="Friendly name"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1 text-gray-600 dark:text-gray-400">Value</label>
          <input
            type="text"
            value={formData.value}
            onChange={(e) => onFormDataChange({ value: e.target.value })}
            className="input w-full py-1.5 text-sm"
            placeholder="Setting value"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1 text-gray-600 dark:text-gray-400">Description</label>
          <input
            type="text"
            value={formData.description}
            onChange={(e) => onFormDataChange({ description: e.target.value })}
            className="input w-full py-1.5 text-sm"
            placeholder="Optional description"
          />
        </div>
      </div>
      <div className="flex gap-2 mt-3">
        <button
          onClick={onCreate}
          disabled={saving || !formData.key || !formData.value}
          className="osrs-btn px-3 py-1.5 text-sm"
        >
          {saving ? 'Creating...' : 'Create'}
        </button>
        <button
          onClick={onCancel}
          className="osrs-btn px-3 py-1.5 text-sm bg-secondary-100 dark:bg-secondary-800 border border-secondary-300 dark:border-secondary-600 hover:bg-secondary-200 dark:hover:bg-secondary-700 text-secondary-900 dark:text-secondary-100"
          disabled={saving}
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

