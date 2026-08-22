import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
          backgroundColor: '#fafaf7',
          color: '#64748b',
          fontSize: '0.9rem',
          fontFamily: 'Inter, sans-serif',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              width: '24px',
              height: '24px',
              border: '2px solid #cbd5e1',
              borderTopColor: '#1e3a8a',
              borderRadius: '50%',
              margin: '0 auto 12px',
              animation: 'spin 0.8s linear infinite',
            }}
          />
          <p>Verifying authentication...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
