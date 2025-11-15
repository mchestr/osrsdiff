import React, { useEffect } from 'react';

export type NotificationType = 'info' | 'error' | 'success' | 'warning';

export interface Notification {
  id: string;
  message: string | React.ReactNode;
  type: NotificationType;
  duration?: number;
}

interface NotificationProps {
  notification: Notification;
  onClose: (id: string) => void;
}

export const Notification: React.FC<NotificationProps> = ({ notification, onClose }) => {
  useEffect(() => {
    const duration = notification.duration ?? 5000;
    if (duration > 0) {
      const timer = setTimeout(() => {
        onClose(notification.id);
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [notification.id, notification.duration, onClose]);

  const getTypeColor = () => {
    switch (notification.type) {
      case 'error':
        return '#d32f2f';
      case 'success':
        return '#4caf50';
      case 'warning':
        return '#ff9800';
      default:
        return '#ffd700';
    }
  };

  const getTypeBgColor = () => {
    switch (notification.type) {
      case 'error':
        return 'bg-red-900/90 dark:bg-red-900/95';
      case 'success':
        return 'bg-green-900/90 dark:bg-green-900/95';
      case 'warning':
        return 'bg-orange-900/90 dark:bg-orange-900/95';
      default:
        return 'bg-yellow-900/90 dark:bg-yellow-900/95';
    }
  };

  return (
    <div
      className={`osrs-card mb-3 min-w-[300px] max-w-md shadow-lg ${getTypeBgColor()}`}
      style={{
        border: `2px solid ${getTypeColor()}`,
        animation: 'slideInRight 0.3s ease-out',
      }}
    >
      <div className="flex items-start justify-between px-4 py-3">
        <div className="flex-1 pr-3">
          <div className="osrs-text text-sm">{notification.message}</div>
        </div>
        <button
          onClick={() => onClose(notification.id)}
          className="flex-shrink-0 text-gray-400 hover:text-gray-200 transition-colors"
          aria-label="Close notification"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <style>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
};

