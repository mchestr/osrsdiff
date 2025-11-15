import React from 'react';
import { Notification, type Notification as NotificationType } from './Notification';

interface NotificationContainerProps {
  notifications: NotificationType[];
  onClose: (id: string) => void;
}

export const NotificationContainer: React.FC<NotificationContainerProps> = ({
  notifications,
  onClose,
}) => {
  if (notifications.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[100] flex flex-col items-end"
      style={{ pointerEvents: 'none' }}
    >
      <div style={{ pointerEvents: 'auto' }}>
        {notifications.map((notification) => (
          <Notification
            key={notification.id}
            notification={notification}
            onClose={onClose}
          />
        ))}
      </div>
    </div>
  );
};

