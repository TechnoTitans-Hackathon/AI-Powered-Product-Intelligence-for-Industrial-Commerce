import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserInfo, loginUser, getAuthMe } from '../api/client';

interface AuthContextType {
  isAuthenticated: boolean;
  user: UserInfo | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('auth_token'));
  const [user, setUser] = useState<UserInfo | null>(() => {
    const saved = localStorage.getItem('user_info');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const checkAuth = async () => {
      const savedToken = localStorage.getItem('auth_token');
      if (savedToken) {
        try {
          const data = await getAuthMe();
          if (data && data.user) {
            setUser(data.user);
            localStorage.setItem('user_info', JSON.stringify(data.user));
          }
        } catch (e) {
          console.warn('Auth token validation failed, clearing session:', e);
          // Token is invalid/expired
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user_info');
          setToken(null);
          setUser(null);
        }
      } else {
        setToken(null);
        setUser(null);
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await loginUser({ email, password });
    if (res && res.access_token) {
      setToken(res.access_token);
      setUser(res.user);
      localStorage.setItem('auth_token', res.access_token);
      localStorage.setItem('user_info', JSON.stringify(res.user));
      if (res.tenant) {
        localStorage.setItem('active_tenant_id', res.tenant.id);
        localStorage.setItem('active_tenant_name', res.tenant.name);
      }
      window.dispatchEvent(new Event('auth-changed'));
      window.dispatchEvent(new Event('tenant-changed'));
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_info');
    localStorage.removeItem('active_tenant_id');
    localStorage.removeItem('active_tenant_name');
    setToken(null);
    setUser(null);
    window.dispatchEvent(new Event('auth-changed'));
    window.dispatchEvent(new Event('tenant-changed'));
  };

  const isAuthenticated = Boolean(token);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        user,
        token,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
