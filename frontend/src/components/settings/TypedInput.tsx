import React from 'react';
import { SelectDropdown } from './SelectDropdown';
import type { Setting } from './types';

interface TypedInputProps {
  setting: Setting;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export const TypedInput: React.FC<TypedInputProps> = ({ setting, value, onChange, disabled = false }) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value);
  };

  const inputClasses = "input w-full py-1 text-xs";

  switch (setting.setting_type) {
    case 'boolean':
      return (
        <SelectDropdown
          value={value}
          options={[
            { value: 'true', label: 'True' },
            { value: 'false', label: 'False' },
          ]}
          onChange={onChange}
          disabled={disabled}
          className="py-1 text-xs"
        />
      );

    case 'number':
      return (
        <input
          type="number"
          value={value}
          onChange={handleChange}
          disabled={disabled}
          className={inputClasses}
          step={setting.key.includes('temperature') ? '0.1' : '1'}
        />
      );

    case 'enum':
      if (setting.allowed_values && setting.allowed_values.length > 0) {
        return (
          <SelectDropdown
            value={value}
            options={setting.allowed_values.map((val) => ({
              value: val,
              label: val,
            }))}
            onChange={onChange}
            disabled={disabled}
            className="py-1 text-xs"
          />
        );
      }
      // Fallback to text input if enum but no allowed values
      return (
        <input
          type="text"
          value={value}
          onChange={handleChange}
          disabled={disabled}
          className={inputClasses}
        />
      );

    case 'string':
    default:
      // Use password type for secret settings
      return (
        <input
          type={setting.is_secret ? 'password' : 'text'}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          className={inputClasses}
        />
      );
  }
};

