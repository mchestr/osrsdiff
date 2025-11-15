import { useEffect, useState } from 'react';
import { axiosInstance } from '../api/apiClient';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Modal } from '../components/Modal';
import { useModal } from '../hooks';
import { extractErrorMessage } from '../utils/errorHandler';
import {
  type Setting,
  type SettingFormData,
  groupSettingsBySection,
  SettingEditModal,
  SettingsTable,
} from '../components/settings';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingSetting, setEditingSetting] = useState<Setting | null>(null);
  const [formData, setFormData] = useState<SettingFormData>({
    key: '',
    value: '',
    display_name: '',
    description: '',
    setting_type: 'string',
    allowed_values: [],
  });
  const [showEditModal, setShowEditModal] = useState(false);

  const { modalState, showModal, closeModal } = useModal();

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get('/api/v1/settings');
      setSettings(response.data.settings);
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to fetch settings');
      showModal('Error', errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRowClick = (setting: Setting, e: React.MouseEvent) => {
    // Don't open modal if clicking on action buttons
    const target = e.target as HTMLElement;
    if (target.closest('button')) {
      return;
    }
    handleEdit(setting);
  };

  const handleEdit = (setting: Setting) => {
    setEditingSetting(setting);
    setFormData({
      key: setting.key,
      value: setting.value,
      display_name: setting.display_name || '',
      description: setting.description || '',
      setting_type: setting.setting_type || 'string',
      allowed_values: setting.allowed_values || [],
    });
    setShowEditModal(true);
  };

  const handleCancelEdit = () => {
    setShowEditModal(false);
    setEditingSetting(null);
    setFormData({
      key: '',
      value: '',
      display_name: '',
      description: '',
      setting_type: 'string',
      allowed_values: [],
    });
  };

  const handleSave = async () => {
    if (!editingSetting) return;

    setSaving(true);
    try {
      await axiosInstance.put(`/api/v1/settings/${editingSetting.key}`, {
        value: formData.value,
        setting_type: formData.setting_type,
        allowed_values: formData.allowed_values.length > 0 ? formData.allowed_values : null,
      });
      showModal('Success', 'Setting updated successfully', 'success');
      await fetchSettings();
      handleCancelEdit();
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to update setting');
      showModal('Error', errorMessage, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async (key: string) => {
    if (!confirm(`Are you sure you want to reset setting "${key}" to its default value?`)) {
      return;
    }

    setSaving(true);
    try {
      await axiosInstance.post(`/api/v1/settings/${key}/reset`);
      showModal('Success', 'Setting reset to default successfully', 'success');
      await fetchSettings();
    } catch (error: unknown) {
      const errorMessage = extractErrorMessage(error, 'Failed to reset setting');
      showModal('Error', errorMessage, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading settings..." />;
  }

  const sections = groupSettingsBySection(settings);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="osrs-card-title text-2xl sm:text-3xl mb-0">Settings</h1>
      </div>

      {/* Compact Settings Display */}
      {settings.length === 0 ? (
        <div className="osrs-card p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">No settings found.</p>
        </div>
      ) : (
        <SettingsTable
          sections={sections}
          onRowClick={handleRowClick}
          onEdit={handleEdit}
          onReset={handleReset}
          disabled={saving}
        />
      )}

      {/* Edit Modal */}
      {showEditModal && editingSetting && (
        <SettingEditModal
          setting={editingSetting}
          formData={formData}
          onValueChange={(value) => setFormData({ ...formData, value })}
          onSave={handleSave}
          onCancel={handleCancelEdit}
          saving={saving}
        />
      )}

      {/* Message Modal */}
      <Modal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        title={modalState.title}
        type={modalState.type}
      >
        {modalState.message}
      </Modal>
    </div>
  );
};

