import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ListOrdered,
  RefreshCw,
  Play,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { getJobs, getBatchSummary, submitBatchProcessing, getProducts } from '../api/client';
import { ProcessingJobItem, ProductItem } from '../types';
import { useTenant } from '../context/TenantContext';

export const BatchProcessing: React.FC = () => {
  const navigate = useNavigate();
  const { activeTenantId, activeTenantName } = useTenant();
  const [jobs, setJobs] = useState<ProcessingJobItem[]>([]);
  const [summary, setSummary] = useState<{
    total_jobs: number;
    completed: number;
    failed: number;
    processing: number;
    queued: number;
    remaining: number;
  } | null>(null);
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [jobsData, sumData, prodsData] = await Promise.all([
        getJobs({ limit: 50 }),
        getBatchSummary(),
        getProducts({ limit: 100 }),
      ]);
      setJobs(jobsData);
      setSummary(sumData);
      setProducts(prodsData);
    } catch (err) {
      console.error('Error fetching batch data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 4000);
    const handleTenantChange = () => {
      fetchData();
    };
    window.addEventListener('tenant-changed', handleTenantChange);
    return () => {
      clearInterval(interval);
      window.removeEventListener('tenant-changed', handleTenantChange);
    };
  }, [activeTenantId]);


  const handleStartBatch = async () => {
    if (selectedProductIds.length === 0) {
      alert('Please select at least one product to process.');
      return;
    }

    try {
      setSubmitting(true);
      await submitBatchProcessing(selectedProductIds);
      setSelectedProductIds([]);
      await fetchData();
    } catch (err) {
      console.error('Batch submission error:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const toggleProductSelection = (id: string) => {
    setSelectedProductIds((prev) =>
      prev.includes(id) ? prev.filter((pId) => pId !== id) : [...prev, id]
    );
  };

  const selectAllProducts = () => {
    if (selectedProductIds.length === products.length) {
      setSelectedProductIds([]);
    } else {
      setSelectedProductIds(products.map((p) => p.id));
    }
  };

  return (
    <div className="page-body">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f172a' }}>Batch Processing Pipeline</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '2px' }}>
            Queue, monitor, and execute multi-agent product intelligence workflows across catalog batches
          </p>
        </div>
        <button className="btn-secondary" onClick={fetchData} disabled={loading}>
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* KPI Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Jobs Executed</div>
          <div className="stat-value">{summary?.total_jobs ?? 0}</div>
        </div>
        <div className="stat-card" style={{ borderLeft: '4px solid #10b981' }}>
          <div className="stat-label">Completed Successfully</div>
          <div className="stat-value" style={{ color: '#059669' }}>{summary?.completed ?? 0}</div>
        </div>
        <div className="stat-card" style={{ borderLeft: '4px solid #3b82f6' }}>
          <div className="stat-label">In Progress / Queued</div>
          <div className="stat-value" style={{ color: '#2563eb' }}>{summary?.remaining ?? 0}</div>
        </div>
        <div className="stat-card" style={{ borderLeft: '4px solid #ef4444' }}>
          <div className="stat-label">Failed Jobs</div>
          <div className="stat-value" style={{ color: '#dc2626' }}>{summary?.failed ?? 0}</div>
        </div>
      </div>

      {/* Batch Trigger Panel */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <div>
            <h2 className="card-title">Launch New Batch Job</h2>
            <p style={{ fontSize: '0.785rem', color: '#64748b', marginTop: '2px' }}>
              Select catalog items to run through the multi-agent enrichment pipeline
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn-secondary btn-sm" onClick={selectAllProducts}>
              {selectedProductIds.length === products.length ? 'Deselect All' : 'Select All'}
            </button>
            <button
              className="btn-primary btn-sm"
              onClick={handleStartBatch}
              disabled={submitting || selectedProductIds.length === 0}
            >
              <Play size={13} />
              Process {selectedProductIds.length} Products
            </button>
          </div>
        </div>

        {/* Product selection pills */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', maxHeight: '120px', overflowY: 'auto', padding: '4px' }}>
          {products.map((p) => {
            const isSelected = selectedProductIds.includes(p.id);
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => toggleProductSelection(p.id)}
                style={{
                  padding: '4px 10px',
                  borderRadius: '16px',
                  fontSize: '0.75rem',
                  border: isSelected ? '1px solid #2563eb' : '1px solid #cbd5e1',
                  backgroundColor: isSelected ? '#eff6ff' : '#ffffff',
                  color: isSelected ? '#1e40af' : '#475569',
                  cursor: 'pointer',
                  fontWeight: isSelected ? 600 : 400,
                }}
              >
                {p.name} ({p.mpn || p.sku})
              </button>
            );
          })}
        </div>
      </div>

      {/* Jobs Table */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Processing Jobs History</h2>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Product ID</th>
                <th>Status</th>
                <th>Pipeline Stage</th>
                <th>Progress</th>
                <th>Time (ms)</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '32px', color: '#94a3b8' }}>
                    No batch processing jobs yet.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: '#475569' }}>
                        {job.id.slice(0, 8)}...
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontFamily: 'monospace',
                          fontSize: '0.8rem',
                          color: '#2563eb',
                          cursor: 'pointer',
                        }}
                        onClick={() => navigate(`/product-intelligence?id=${job.product_id}`)}
                      >
                        {job.product_id.slice(0, 8)}...
                      </span>
                    </td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          backgroundColor:
                            job.status === 'COMPLETED'
                              ? '#ecfdf5'
                              : job.status === 'PROCESSING'
                              ? '#eff6ff'
                              : job.status === 'FAILED'
                              ? '#fef2f2'
                              : '#f1f5f9',
                          color:
                            job.status === 'COMPLETED'
                              ? '#065f46'
                              : job.status === 'PROCESSING'
                              ? '#1e40af'
                              : job.status === 'FAILED'
                              ? '#991b1b'
                              : '#475569',
                        }}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8rem', color: '#334155' }}>
                      {job.pipeline_stage || job.step}
                    </td>
                    <td style={{ width: '160px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div
                          style={{
                            flex: 1,
                            height: '6px',
                            backgroundColor: '#e2e8f0',
                            borderRadius: '3px',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              width: `${job.progress}%`,
                              height: '100%',
                              backgroundColor: job.status === 'FAILED' ? '#ef4444' : '#10b981',
                              transition: 'width 0.3s ease',
                            }}
                          />
                        </div>
                        <span style={{ fontSize: '0.725rem', color: '#64748b', minWidth: '32px' }}>
                          {job.progress}%
                        </span>
                      </div>
                    </td>
                    <td style={{ fontSize: '0.8rem', color: '#64748b' }}>
                      {job.processing_time_ms ? `${job.processing_time_ms.toFixed(0)} ms` : '—'}
                    </td>
                    <td style={{ fontSize: '0.785rem', color: '#64748b' }}>
                      {job.created_at ? new Date(job.created_at).toLocaleTimeString() : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
