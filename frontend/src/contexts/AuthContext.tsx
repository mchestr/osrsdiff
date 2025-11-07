import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api, decodeToken } from '../lib/apiClient';

interface User {
  username: string;
  user_id: number;
  is_admin: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const decoded = decodeToken(token);
          if (decoded && decoded.exp * 1000 > Date.now()) {
            const userData = await api.AuthenticationService.getCurrentUserInfoAuthMeGet();
            setUser({
              username: userData.username,
              user_id: userData.user_id,
              is_admin: decoded.is_admin || false,
            });
          } else {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
          }
        } catch (error) {
          console.error('Failed to initialize auth:', error);
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (username: string, password: string) => {
    const formData = {
      username,
      password,
      grant_type: 'password',
    };
    const response = await api.AuthenticationService.loginAuthLoginPost(formData);
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);

    const decoded = decodeToken(response.access_token);
    const userData = await api.AuthenticationService.getCurrentUserInfoAuthMeGet();
    setUser({
      username: userData.username,
      user_id: userData.user_id,
      is_admin: decoded.is_admin || false,
    });
  };

  const logout = async () => {
    try {
      await api.AuthenticationService.logoutAuthLogoutPost();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        isAuthenticated: !!user,
        isAdmin: user?.is_admin || false,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

