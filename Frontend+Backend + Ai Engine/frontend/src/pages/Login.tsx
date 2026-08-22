import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, AlertCircle, Loader2, KeyRound, Mail } from 'lucide-react';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();

  const [email, setEmail] = useState('employee@demo.com');
  const [password, setPassword] = useState('demo123');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // If already authenticated, redirect to dashboard
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      const from = (location.state as any)?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, authLoading, navigate, location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError('Please enter both work email and password.');
      return;
    }

    try {
      setError(null);
      setIsSubmitting(true);
      await login(email.trim(), password);
      const from = (location.state as any)?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    } catch (err: any) {
      console.error('Login error:', err);
      if (err?.response?.status === 401 || err?.response?.data?.detail) {
        setError('Invalid email or password.');
      } else {
        setError('Invalid email or password.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const fillPrototypeCredentials = () => {
    setEmail('employee@demo.com');
    setPassword('demo123');
    setError(null);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#fafaf7',
        padding: '24px 16px',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      {/* Brand Header */}
      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '10px',
            marginBottom: '8px',
          }}
        >
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: '#1e3a8a',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
            }}
          >
            <ShieldCheck size={20} />
          </div>
          <span
            style={{
              fontSize: '1.25rem',
              fontWeight: 700,
              color: '#0f172a',
              letterSpacing: '-0.02em',
            }}
          >
            Product Intelligence Platform
          </span>
        </div>
        <p style={{ fontSize: '0.875rem', color: '#64748b', margin: 0 }}>
          Autonomous Multi-Agent Catalog Intelligence System
        </p>
      </div>

      {/* Main Login Card */}
      <div
        style={{
          width: '100%',
          maxWidth: '400px',
          backgroundColor: '#ffffff',
          borderRadius: '8px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.04), 0 2px 4px -1px rgba(0, 0, 0, 0.02)',
          padding: '32px 28px',
        }}
      >
        <div style={{ marginBottom: '24px', textAlign: 'left' }}>
          <h1
            style={{
              fontSize: '1.15rem',
              fontWeight: 600,
              color: '#0f172a',
              marginBottom: '4px',
            }}
          >
            Employee Login
          </h1>
          <p style={{ fontSize: '0.8rem', color: '#64748b', margin: 0 }}>
            Sign in to access workspace catalogs and intelligence pipelines
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 12px',
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '6px',
              color: '#991b1b',
              fontSize: '0.825rem',
              marginBottom: '20px',
            }}
          >
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Work Email */}
          <div>
            <label
              htmlFor="email-input"
              style={{
                display: 'block',
                fontSize: '0.8rem',
                fontWeight: 500,
                color: '#334155',
                marginBottom: '6px',
              }}
            >
              Work Email
            </label>
            <div style={{ position: 'relative' }}>
              <Mail
                size={16}
                style={{
                  position: 'absolute',
                  left: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: '#94a3b8',
                }}
              />
              <input
                id="email-input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                disabled={isSubmitting}
                style={{
                  width: '100%',
                  padding: '9px 12px 9px 36px',
                  fontSize: '0.875rem',
                  color: '#0f172a',
                  backgroundColor: '#ffffff',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <label
              htmlFor="password-input"
              style={{
                display: 'block',
                fontSize: '0.8rem',
                fontWeight: 500,
                color: '#334155',
                marginBottom: '6px',
              }}
            >
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <KeyRound
                size={16}
                style={{
                  position: 'absolute',
                  left: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: '#94a3b8',
                }}
              />
              <input
                id="password-input"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                disabled={isSubmitting}
                style={{
                  width: '100%',
                  padding: '9px 12px 9px 36px',
                  fontSize: '0.875rem',
                  color: '#0f172a',
                  backgroundColor: '#ffffff',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              width: '100%',
              padding: '10px 16px',
              marginTop: '4px',
              backgroundColor: '#1e3a8a',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              opacity: isSubmitting ? 0.75 : 1,
              transition: 'background-color 0.15s ease',
            }}
          >
            {isSubmitting ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Authenticating...</span>
              </>
            ) : (
              <span>Login</span>
            )}
          </button>
        </form>

        {/* Prototype Demonstration Credentials */}
        <div
          style={{
            marginTop: '24px',
            padding: '14px',
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '6px',
            textAlign: 'left',
          }}
        >
          <div
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: '#475569',
              marginBottom: '8px',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            Prototype credentials for demonstration
          </div>
          <div
            style={{
              fontSize: '0.8rem',
              color: '#334155',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            <div>
              <span style={{ color: '#64748b', fontFamily: 'Inter, sans-serif' }}>Email: </span>
              <strong>employee@demo.com</strong>
            </div>
            <div>
              <span style={{ color: '#64748b', fontFamily: 'Inter, sans-serif' }}>Password: </span>
              <strong>demo123</strong>
            </div>
          </div>
          <button
            type="button"
            onClick={fillPrototypeCredentials}
            style={{
              marginTop: '10px',
              fontSize: '0.75rem',
              color: '#1e3a8a',
              background: 'none',
              border: 'none',
              padding: 0,
              textDecoration: 'underline',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            Auto-fill demonstration credentials
          </button>
        </div>
      </div>

      {/* Footer Info */}
      <div style={{ marginTop: '24px', textAlign: 'center', fontSize: '0.75rem', color: '#94a3b8' }}>
        Product Intelligence Platform • Hackathon Prototype
      </div>
    </div>
  );
};
