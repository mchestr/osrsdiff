import React, { createContext, useContext, ReactNode } from 'react';
import { useNotification, type UseNotificationReturn } from '../hooks/useNotification';
import { NotificationContainer } from '../components/NotificationContainer';

const NotificationContext = createContext<UseNotificationReturn | undefined>(undefined);

interface NotificationProviderProps {
  children: ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const notification = useNotification();

  return (
    <NotificationContext.Provider value={notification}>
      {children}
      <NotificationContainer
        notifications={notification.notifications}
        onClose={notification.removeNotification}
      />
    </NotificationContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useNotificationContext = (): UseNotificationReturn => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotificationContext must be used within NotificationProvider');
  }
  return context;
};

