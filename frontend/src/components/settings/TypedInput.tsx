import React from 'react';
import { Input, Select } from '../ui';
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

  switch (setting.setting_type) {
    case 'boolean':
      return (
        <Select
          value={value}
          options={[
            { value: 'true', label: 'True' },
            { value: 'false', label: 'False' },
          ]}
          onChange={onChange}
          disabled={disabled}
        />
      );

    case 'number':
      return (
        <Input
          type="number"
          value={value}
          onChange={handleChange}
          disabled={disabled}
          step={setting.key.includes('temperature') ? '0.1' : '1'}
        />
      );

    case 'enum':
      if (setting.allowed_values && setting.allowed_values.length > 0) {
        return (
          <Select
            value={value}
            options={setting.allowed_values.map((val) => ({
              value: val,
              label: val,
            }))}
            onChange={onChange}
            disabled={disabled}
          />
        );
      }
      // Fallback to text input if enum but no allowed values
      return (
        <Input
          type="text"
          value={value}
          onChange={handleChange}
          disabled={disabled}
        />
      );

    case 'string':
    default:
      // Use password type for secret settings
      return (
        <Input
          type={setting.is_secret ? 'password' : 'text'}
          value={value}
          onChange={handleChange}
          disabled={disabled}
        />
      );
  }
};

