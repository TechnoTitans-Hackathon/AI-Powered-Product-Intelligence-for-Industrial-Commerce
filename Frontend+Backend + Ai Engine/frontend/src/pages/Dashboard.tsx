import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Package,
  AlertTriangle,
  CheckCircle,
  Clock,
  ArrowRight,
  RefreshCw,
  Sparkles,
  Upload,
  Globe,
  Building2,
} from 'lucide-react';
import { getAnalyticsSummary, getRecentActivity, getRecentlyProcessed } from '../api/client';
import { AnalyticsSummary, RecentActivityItem, RecentlyProcessedItem } from '../types';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { StatusBadge } from '../components/StatusBadge';
import { useTenant } from '../context/TenantContext';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { activeTenantId, activeTenantName, switchTenant } = useTenant();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [activities, setActivities] = useState<RecentActivityItem[]>([]);
  const [recentProducts, setRecentProducts] = useState<RecentlyProcessedItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [sumData, actData, recData] = await Promise.all([
        getAnalyticsSummary(),
        getRecentActivity(8),
        getRecentlyProcessed(6),
      ]);
      setSummary(sumData);
      setActivities(actData);
      setRecentProducts(recData);
    } catch (err) {
      console.error('Error loading dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }, [activeTenantId]);

  useEffect(() => {
    fetchData();
    const handleTenantChange = () => {
      fetchData();
    };
    window.addEventListener('tenant-changed', handleTenantChange);
    return () => {
      window.removeEventListener('tenant-changed', handleTenantChange);
    };
  }, [fetchData]);

  const formatRelativeTime = (timestamp?: string) => {
    if (!timestamp) return 'Recently';
    const date = new Date(timestamp);
    const diffSeconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diffSeconds < 60) return 'Just now';
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} min ago`;
    if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)} hrs ago`;
    return `${Math.floor(diffSeconds / 86400)} days ago`;
  };

  const isZeroState = summary && summary.products.total === 0;

  return (
    <div className="page-body">
      {/* Welcome Banner */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '24px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f172a' }}>Product Intelligence Dashboard</h1>
            <span
              style={{
                fontSize: '0.75rem',
                padding: '2px 8px',
                backgroundColor: activeTenantId === 'demo' ? '#f1f5f9' : '#eff6ff',
                color: activeTenantId === 'demo' ? '#475569' : '#1d4ed8',
                borderRadius: '4px',
                fontWeight: 600,
              }}
            >
              {activeTenantName}
            </span>
          </div>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '4px' }}>
            Multi-agent industrial catalog enrichment, validation, and explainability platform
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn-secondary" onClick={fetchData} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button className="btn-primary" onClick={() => navigate('/upload')}>
            <Sparkles size={15} />
            Upload Product
          </button>
        </div>
      </div>

      {/* Zero State Onboarding for New Companies */}
      {isZeroState ? (
        <div
          style={{
            backgroundColor: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '12px',
            padding: '40px 24px',
            textAlign: 'center',
            marginBottom: '24px',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
          }}
        >
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '12px',
              backgroundColor: '#eff6ff',
              color: '#2563eb',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px auto',
            }}
          >
            <Building2 size={28} />
          </div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a', marginBottom: '6px' }}>
            Welcome to {activeTenantName} Workspace
          </h2>
          <p style={{ fontSize: '0.875rem', color: '#64748b', maxWidth: '520px', margin: '0 auto 24px auto' }}>
            This company tenant currently has a clean empty catalog. Start by uploading your product spreadsheet, ingesting an online URL, or explore the demo tenant dataset.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <button
              className="btn-primary"
              onClick={() => navigate('/upload')}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px' }}
            >
              <Upload size={16} />
              Upload Batch Catalog (.xlsx / .csv)
            </button>
            <button
              className="btn-secondary"
              onClick={() => navigate('/upload')}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px' }}
            >
              <Globe size={16} />
              Ingest from Web URL
            </button>
            <button
              className="btn-secondary"
              onClick={() => switchTenant('demo')}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px' }}
            >
              <Package size={16} />
              Switch to Demo Catalog (10k Products)
            </button>
          </div>
        </div>
      ) : null}

      {/* Primary KPI Stats Grid (Real metrics only - no fake precision percentages) */}
      <div className="stats-grid">
        <div className="stat-card" style={{ borderLeft: '4px solid #1e3a8a' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div className="stat-label">Total Catalog Products</div>
              <div className="stat-value">{summary?.products.total ?? 0}</div>
            </div>
            <div style={{ padding: '8px', borderRadius: '6px', backgroundColor: '#eff6ff', color: '#1e40af' }}>
              <Package size={20} />
            </div>
          </div>
          <div className="stat-sub">
            <span style={{ color: '#059669', fontWeight: 600 }}>{summary?.products.verified ?? 0}</span> verified by AI
          </div>
        </div>

        <div className="stat-card" style={{ borderLeft: '4px solid #d97706' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div className="stat-label">Missing Data Detected</div>
              <div className="stat-value">{summary?.products.with_missing_data ?? 0}</div>
            </div>
            <div style={{ padding: '8px', borderRadius: '6px', backgroundColor: '#fffbeb', color: '#b45309' }}>
              <AlertTriangle size={20} />
            </div>
          </div>
          <div className="stat-sub">Products with unpopulated required attributes</div>
        </div>

        <div className="stat-card" style={{ borderLeft: '4px solid #dc2626' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div className="stat-label">Issues Needing Attention</div>
              <div className="stat-value">{summary?.validation.needs_attention ?? 0}</div>
            </div>
            <div style={{ padding: '8px', borderRadius: '6px', backgroundColor: '#fef2f2', color: '#dc2626' }}>
              <CheckCircle size={20} />
            </div>
          </div>
          <div className="stat-sub">
            <span style={{ color: '#dc2626', fontWeight: 600 }}>{summary?.products.with_conflicts ?? 0}</span> conflicting sources
          </div>
        </div>

        <div className="stat-card" style={{ borderLeft: '4px solid #059669' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div className="stat-label">Completed Batch Jobs</div>
              <div className="stat-value">{summary?.jobs.completed ?? 0}</div>
            </div>
            <div style={{ padding: '8px', borderRadius: '6px', backgroundColor: '#ecfdf5', color: '#059669' }}>
              <Clock size={20} />
            </div>
          </div>
          <div className="stat-sub">
            Total pipeline executions: {summary?.jobs.total ?? 0}
          </div>
        </div>
      </div>

      {/* Main Grid: Recently Processed Products + Recent Activity */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', alignItems: 'start' }}>
        {/* Left Column: Recently Processed Products Table */}
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="card-title">Recently Processed Products</h2>
              <p style={{ fontSize: '0.785rem', color: '#64748b', marginTop: '2px' }}>
                Products that recently completed multi-agent intelligence enrichment
              </p>
            </div>
            <button className="btn-secondary btn-sm" onClick={() => navigate('/catalog')}>
              View All Catalog
              <ArrowRight size={13} />
            </button>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Part Number / SKU</th>
                  <th>Status</th>
                  <th>Confidence</th>
                  <th>Missing Specs</th>
                  <th>Processed</th>
                </tr>
              </thead>
              <tbody>
                {recentProducts.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: '#94a3b8' }}>
                      No processed products yet for this workspace. Upload your first product or catalog.
                    </td>
                  </tr>
                ) : (
                  recentProducts.map((p) => (
                    <tr
                      key={p.product_id}
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/product-intelligence?id=${p.product_id}`)}
                    >
                      <td>
                        <div style={{ fontWeight: 600, color: '#0f172a' }}>{p.name}</div>
                      </td>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: '#475569' }}>{p.sku}</span>
                      </td>
                      <td>
                        <StatusBadge status={p.status} />
                      </td>
                      <td>
                        <ConfidenceBadge level={p.confidence_level} />
                      </td>
                      <td>
                        {p.missing_fields > 0 ? (
                          <span style={{ color: '#d97706', fontSize: '0.8rem', fontWeight: 500 }}>
                            {p.missing_fields} fields
                          </span>
                        ) : (
                          <span style={{ color: '#059669', fontSize: '0.8rem' }}>Complete</span>
                        )}
                      </td>
                      <td style={{ fontSize: '0.785rem', color: '#64748b' }}>
                        {formatRelativeTime(p.processed_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Recent Activity Feed */}
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="card-title">Recent Activity</h2>
              <p style={{ fontSize: '0.785rem', color: '#64748b', marginTop: '2px' }}>Real-time platform events</p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {activities.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px', color: '#94a3b8', fontSize: '0.85rem' }}>
                No recent activity logged for this workspace.
              </div>
            ) : (
              activities.map((act, index) => (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    padding: '10px',
                    borderRadius: '6px',
                    backgroundColor: '#f8fafc',
                    border: '1px solid #f1f5f9',
                  }}
                >
                  <div
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: act.status === 'success' ? '#10b981' : '#ef4444',
                      marginTop: '6px',
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.825rem', fontWeight: 600, color: '#0f172a' }}>{act.title}</div>
                    <div style={{ fontSize: '0.775rem', color: '#64748b', marginTop: '2px' }}>{act.description}</div>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '4px' }}>
                      {formatRelativeTime(act.timestamp)}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

