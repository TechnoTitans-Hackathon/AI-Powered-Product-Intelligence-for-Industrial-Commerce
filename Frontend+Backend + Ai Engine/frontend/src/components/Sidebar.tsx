import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Upload,
  Cpu,
  Layers,
  ListOrdered,
  CheckSquare,
  FileSearch,
  BarChart3,
  Settings,
  HelpCircle,
  Sparkles,
  Activity,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { label: 'Upload Product', path: '/upload', icon: Upload },
    { label: 'Product Intelligence', path: '/product-intelligence', icon: Cpu },
    { label: 'Product Catalog', path: '/catalog', icon: Layers },
    { label: 'Batch Processing', path: '/batch-processing', icon: ListOrdered },
    { label: 'Validation Center', path: '/validation', icon: CheckSquare },
    { label: 'Explainability', path: '/explainability', icon: FileSearch },
    { label: 'Analytics', path: '/analytics', icon: BarChart3 },
    { label: 'Settings', path: '/settings', icon: Settings },
    { label: 'Help & Support', path: '/help', icon: HelpCircle },
    { label: 'AI Trace Console', path: '/admin/ai-trace', icon: Activity },

  ];

  return (
    <aside
      style={{
        width: '260px',
        backgroundColor: '#1e293b',
        color: '#f8fafc',
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid #0f172a',
        flexShrink: 0,
        height: '100vh',
        position: 'sticky',
        top: 0,
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: '24px 20px 20px 20px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              backgroundColor: '#3b82f6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
            }}
          >
            <Sparkles size={18} />
          </div>
          <div>
            <div style={{ fontSize: '0.95rem', fontWeight: '700', letterSpacing: '-0.02em', color: '#ffffff' }}>
              PRODUCT AI
            </div>
            <div style={{ fontSize: '0.675rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Industrial Intelligence
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav
        style={{
          flex: 1,
          padding: '16px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
          overflowY: 'auto',
        }}
      >
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '9px 12px',
                borderRadius: '6px',
                fontSize: '0.85rem',
                fontWeight: isActive ? 600 : 400,
                color: isActive ? '#ffffff' : '#94a3b8',
                backgroundColor: isActive ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                textDecoration: 'none',
                borderLeft: isActive ? '3px solid #3b82f6' : '3px solid transparent',
                transition: 'all 0.15s ease',
              })}
            >
              <Icon size={16} style={{ flexShrink: 0 }} />
              <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Multi-Agent Engine Status Footer */}
      <div
        style={{
          padding: '16px 20px',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: '#0f172a',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ fontSize: '0.725rem', color: '#94a3b8', fontWeight: 500 }}>AI Engine</span>
          <span
            style={{
              fontSize: '0.675rem',
              color: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              padding: '2px 6px',
              borderRadius: '4px',
              fontWeight: 600,
            }}
          >
            ACTIVE
          </span>
        </div>
        <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Multi-Agent Orchestrator v2.0</div>
      </div>
    </aside>
  );
};
