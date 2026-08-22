import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  CheckSquare,
  AlertTriangle,
  CheckCircle2,
  Filter,
  RefreshCw,
  Eye,
  Edit2,
  XCircle,
} from 'lucide-react';
import { getValidationIssues, getValidationSummary, resolveValidationIssue } from '../api/client';
import { ValidationIssue } from '../types';
import { useTenant } from '../context/TenantContext';

export const ValidationCenter: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { activeTenantId, activeTenantName } = useTenant();
  const filterProductId = searchParams.get('productId');

  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [summary, setSummary] = useState<{
    total_issues: number;
    resolved: number;
    unresolved: number;
    conflicts: number;
    missing_fields: number;
    critical: number;
    high: number;
    needs_attention: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [severityFilter, setSeverityFilter] = useState('All');
  const [resolvedFilter, setResolvedFilter] = useState('unresolved');

  // Edit resolution modal
  const [editingIssue, setEditingIssue] = useState<ValidationIssue | null>(null);
  const [correctedValue, setCorrectedValue] = useState('');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [issueData, sumData] = await Promise.all([
        getValidationIssues({
          product_id: filterProductId || undefined,
          severity: severityFilter !== 'All' ? severityFilter.toLowerCase() : undefined,
          resolved: resolvedFilter === 'All' ? undefined : resolvedFilter === 'resolved',
        }),
        getValidationSummary(),
      ]);
      setIssues(issueData);
      setSummary(sumData);
    } catch (err) {
      console.error('Error loading validation data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const handleTenantChange = () => {
      fetchData();
    };
    window.addEventListener('tenant-changed', handleTenantChange);
    return () => {
      window.removeEventListener('tenant-changed', handleTenantChange);
    };
  }, [filterProductId, severityFilter, resolvedFilter, activeTenantId]);


  const handleQuickResolve = async (issueId: string) => {
    try {
      await resolveValidationIssue(issueId, { resolved: true, reviewer: 'Product Specialist' });
      fetchData();
    } catch (err) {
      console.error('Error resolving issue:', err);
    }
  };

  const handleSaveCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingIssue) return;
    try {
      await resolveValidationIssue(editingIssue.id, {
        resolved: true,
        corrected_value: correctedValue,
        reviewer: 'Product Specialist',
      });
      setEditingIssue(null);
      fetchData();
    } catch (err) {
      console.error('Error saving correction:', err);
    }
  };

  return (
    <div className="page-body">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f172a' }}>Validation Center</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '2px' }}>
            Deterministic rule validation, source discrepancies, and field-level review queue
          </p>
        </div>
        <button className="btn-secondary" onClick={fetchData} disabled={loading}>
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Summary KPI Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Validation Issues</div>
          <div className="stat-value">{summary?.total_issues ?? 0}</div>
        </div>
        <div className="stat-card" style={{ borderLeft: '4px solid #ef4444' }}>
          <div className="stat-label">Unresolved Issues</div>
          <div className="stat-value" style={{ color: '#dc2626' }}>{summary?.unresolved ?? 0}</div>
        </div>
        <div className="stat-card" style={{ borderLeft: '4px solid #d97706' }}>
          <div className="stat-label">Source Conflicts</div>
          <div className="stat-value" style={{ color: '#b45309' }}>{summary?.conflicts ?? 0}</div>
        </div>
        <div className="stat-card" style={{ borderLeft: '4px solid #10b981' }}>
          <div className="stat-label">Resolved & Approved</div>
          <div className="stat-value" style={{ color: '#059669' }}>{summary?.resolved ?? 0}</div>
        </div>
      </div>

      {/* Filters Card */}
      <div className="card" style={{ padding: '14px 18px', marginBottom: '18px' }}>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569' }}>Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              style={{ width: '160px' }}
            >
              <option value="All">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569' }}>Status:</span>
            <select
              value={resolvedFilter}
              onChange={(e) => setResolvedFilter(e.target.value)}
              style={{ width: '160px' }}
            >
              <option value="unresolved">Unresolved Only</option>
              <option value="resolved">Resolved Only</option>
              <option value="All">All Issues</option>
            </select>
          </div>

          {filterProductId && (
            <button
              className="btn-secondary btn-sm"
              onClick={() => navigate('/validation')}
              style={{ fontSize: '0.75rem', color: '#2563eb' }}
            >
              Clear Product Filter ({filterProductId.slice(0, 8)}...)
            </button>
          )}
        </div>
      </div>

      {/* Validation Issues Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Severity</th>
              <th>Type</th>
              <th>Field</th>
              <th>Validation Message</th>
              <th>Values / Suggestion</th>
              <th style={{ textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '36px', color: '#64748b' }}>
                  Loading validation issues...
                </td>
              </tr>
            ) : issues.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: '#059669' }}>
                  <CheckCircle2 size={24} style={{ margin: '0 auto 8px auto' }} />
                  <div>No validation issues matching current criteria.</div>
                </td>
              </tr>
            ) : (
              issues.map((issue) => (
                <tr key={issue.id}>
                  {/* Product Name */}
                  <td style={{ maxWidth: '200px' }}>
                    <div
                      style={{
                        fontWeight: 600,
                        color: '#2563eb',
                        fontSize: '0.825rem',
                        cursor: 'pointer',
                      }}
                      onClick={() => navigate(`/product-intelligence?id=${issue.product_id || issue.productId}`)}
                    >
                      {issue.product_name || issue.productName || 'Product'}
                    </div>
                  </td>

                  {/* Severity */}
                  <td>
                    <span
                      style={{
                        fontSize: '0.725rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        backgroundColor:
                          issue.severity === 'critical' || issue.severity === 'high' ? '#fee2e2' : '#fef3c7',
                        color: issue.severity === 'critical' || issue.severity === 'high' ? '#991b1b' : '#92400e',
                      }}
                    >
                      {issue.severity}
                    </span>
                  </td>

                  {/* Type */}
                  <td style={{ fontSize: '0.8rem', color: '#475569' }}>{issue.type}</td>

                  {/* Field */}
                  <td>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', fontWeight: 600, color: '#0f172a' }}>
                      {issue.field}
                    </span>
                  </td>

                  {/* Validation Message */}
                  <td style={{ fontSize: '0.8rem', color: '#334155', maxWidth: '320px' }}>
                    {issue.message}
                  </td>

                  {/* Values / Suggestion */}
                  <td style={{ fontSize: '0.785rem', color: '#64748b' }}>
                    {issue.current_value && (
                      <div>
                        Value A: <strong style={{ color: '#0f172a' }}>{issue.current_value}</strong>
                      </div>
                    )}
                    {issue.suggested_value && (
                      <div>
                        Value B: <strong style={{ color: '#059669' }}>{issue.suggested_value}</strong>
                      </div>
                    )}
                  </td>

                  {/* Action */}
                  <td style={{ textAlign: 'right' }}>
                    {issue.resolved ? (
                      <span style={{ fontSize: '0.75rem', color: '#059669', fontWeight: 600 }}>Resolved</span>
                    ) : (
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                        <button
                          className="btn-secondary btn-sm"
                          onClick={() => {
                            setEditingIssue(issue);
                            setCorrectedValue(issue.suggested_value || issue.current_value || '');
                          }}
                          title="Correct value"
                        >
                          <Edit2 size={13} />
                        </button>
                        <button
                          className="btn-primary btn-sm"
                          onClick={() => handleQuickResolve(issue.id)}
                          title="Mark resolved"
                        >
                          Resolve
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Correction Modal */}
      {editingIssue && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '480px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '8px' }}>Resolve Validation Anomaly</h3>
            <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '16px' }}>
              Field: <strong>{editingIssue.field}</strong> • {editingIssue.message}
            </p>

            <form onSubmit={handleSaveCorrection}>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '6px' }}>
                  Correct Verified Value
                </label>
                <input
                  type="text"
                  required
                  value={correctedValue}
                  onChange={(e) => setCorrectedValue(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button type="button" className="btn-secondary" onClick={() => setEditingIssue(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Save & Resolve
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
