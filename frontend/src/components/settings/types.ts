export interface Setting {
  id: number;
  key: string;
  value: string;
  display_name: string | null;
  description: string | null;
  setting_type: string;
  allowed_values: string[] | null;
  is_secret: boolean;
  created_at: string;
  updated_at: string;
}

export interface SettingFormData {
  key: string;
  value: string;
  display_name: string;
  description: string;
  setting_type: string;
  allowed_values: string[];
}

export interface SettingSection {
  title: string;
  description: string;
  settings: Setting[];
}

