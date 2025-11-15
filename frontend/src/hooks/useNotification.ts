import { useState, useCallback } from 'react';
import type { Notification, NotificationType } from '../components/Notification';

export interface UseNotificationReturn {
  showNotification: (
    message: string | React.ReactNode,
    type?: NotificationType,
    duration?: number
  ) => void;
  notifications: Notification[];
  removeNotification: (id: string) => void;
}

/**
 * Custom hook for managing notification state consistently across components
 */
export const useNotification = (): UseNotificationReturn => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const showNotification = useCallback(
    (
      message: string | React.ReactNode,
      type: NotificationType = 'info',
      duration: number = 5000
    ) => {
      const id = `notification-${Date.now()}-${Math.random()}`;
      const notification: Notification = {
        id,
        message,
        type,
        duration,
      };

      setNotifications((prev) => [...prev, notification]);
    },
    []
  );

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  return {
    showNotification,
    notifications,
    removeNotification,
  };
};

