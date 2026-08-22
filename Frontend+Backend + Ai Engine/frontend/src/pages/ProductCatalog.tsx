import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Search,
  Filter,
  MoreVertical,
  Plus,
  RefreshCw,
  Eye,
  CheckSquare,
  FileSearch,
  RotateCw,
  Trash2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { getProducts, triggerProductReprocess, deleteProduct } from '../api/client';
import { ProductItem } from '../types';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { StatusBadge } from '../components/StatusBadge';
import { useTenant } from '../context/TenantContext';

export const ProductCatalog: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { activeTenantId, activeTenantName } = useTenant();

  const [products, setProducts] = useState<ProductItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Filter states
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [category, setCategory] = useState(searchParams.get('category') || 'All');
  const [status, setStatus] = useState(searchParams.get('status') || 'All');
  const [confidence, setConfidence] = useState(searchParams.get('confidence') || 'All');

  // Active dropdown menu for 3-dots
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  const fetchProducts = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getProducts({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        search: search.trim() || undefined,
        category: category !== 'All' ? category : undefined,
        status: status !== 'All' ? status : undefined,
        confidence_level: confidence !== 'All' ? confidence : undefined,
      });
      setProducts(data);
    } catch (err) {
      console.error('Error fetching products:', err);
    } finally {
      setLoading(false);
    }
  }, [activeTenantId, page, category, status, confidence]);

  useEffect(() => {
    fetchProducts();
    const handleTenantChange = () => {
      setPage(1);
      fetchProducts();
    };
    window.addEventListener('tenant-changed', handleTenantChange);
    return () => {
      window.removeEventListener('tenant-changed', handleTenantChange);
    };
  }, [fetchProducts]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchProducts();
  };


  const handleReprocess = async (productId: string) => {
    try {
      setActiveMenuId(null);
      await triggerProductReprocess(productId);
      fetchProducts();
    } catch (err) {
      console.error('Reprocess error:', err);
    }
  };

  const handleDelete = async (productId: string) => {
    if (window.confirm('Are you sure you want to delete this product?')) {
      try {
        setActiveMenuId(null);
        await deleteProduct(productId);
        fetchProducts();
      } catch (err) {
        console.error('Delete error:', err);
      }
    }
  };

  return (
    <div className="page-body">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f172a' }}>Product Catalog</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '2px' }}>
            Structured industrial products enriched with dynamic specifications and multi-agent intelligence
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn-secondary" onClick={fetchProducts} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button className="btn-primary" onClick={() => navigate('/upload')}>
            <Plus size={15} />
            Add Product
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="card" style={{ padding: '14px 18px', marginBottom: '18px' }}>
        <form
          onSubmit={handleSearchSubmit}
          style={{
            display: 'grid',
            gridTemplateColumns: '2fr 1fr 1fr 1fr auto',
            gap: '12px',
            alignItems: 'center',
          }}
        >
          {/* Search Input */}
          <div style={{ position: 'relative' }}>
            <Search
              size={15}
              style={{
                position: 'absolute',
                left: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#94a3b8',
              }}
            />
            <input
              type="search"
              placeholder="Search by part number, name, brand, description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ paddingLeft: '32px' }}
            />
          </div>

          {/* Category Filter */}
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="All">All Categories</option>
            <option value="Abrasives">Abrasives & Cutting</option>
            <option value="Bearings">Bearings & Power Transmission</option>
            <option value="Hydraulics">Hydraulics & Fluid Power</option>
            <option value="Motors">Motors & Drives</option>
            <option value="Woodworking">Woodworking Machinery</option>
          </select>

          {/* Status Filter */}
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="All">All Statuses</option>
            <option value="verified">Verified</option>
            <option value="needs_review">Needs Review</option>
            <option value="conflicting">Conflicting</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
          </select>

          {/* Qualitative Confidence Filter */}
          <select value={confidence} onChange={(e) => setConfidence(e.target.value)}>
            <option value="All">All Confidence</option>
            <option value="HIGH">HIGH Confidence</option>
            <option value="MEDIUM">MEDIUM Confidence</option>
            <option value="LOW">LOW Confidence</option>
            <option value="CONFLICT">CONFLICT / Discrepancy</option>
          </select>

          <button type="submit" className="btn-primary">
            <Filter size={14} />
            Filter
          </button>
        </form>
      </div>

      {/* Catalog Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Product Identity</th>
              <th>Category</th>
              <th>Part Number / MPN</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Missing Data</th>
              <th>Key Specifications</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '36px', color: '#64748b' }}>
                  Loading catalog products...
                </td>
              </tr>
            ) : products.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
                  No matching industrial products found.
                </td>
              </tr>
            ) : (
              products.map((p) => {
                // Collect 2-3 prominent dynamic attributes for quick table preview
                const specSnippet = (p.dynamicAttributes || [])
                  .filter((a) => a.value && a.key !== 'feature')
                  .slice(0, 2)
                  .map((a) => `${a.key}: ${a.value}${a.unit ? ' ' + a.unit : ''}`)
                  .join(' • ');

                return (
                  <tr key={p.id} style={{ position: 'relative' }}>
                    {/* Name & Brand */}
                    <td
                      style={{ cursor: 'pointer', maxWidth: '280px' }}
                      onClick={() => navigate(`/product-intelligence?id=${p.id}`)}
                    >
                      <div style={{ fontWeight: 600, color: '#0f172a', fontSize: '0.875rem' }}>{p.name}</div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>
                        Brand: <span style={{ fontWeight: 500, color: '#334155' }}>{p.brand}</span>
                      </div>
                    </td>

                    {/* Category */}
                    <td style={{ fontSize: '0.8rem', color: '#475569' }}>{p.category}</td>

                    {/* SKU / MPN */}
                    <td>
                      <span
                        style={{
                          fontFamily: 'monospace',
                          fontSize: '0.8rem',
                          backgroundColor: '#f1f5f9',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          color: '#0f172a',
                        }}
                      >
                        {p.mpn || p.sku || 'N/A'}
                      </span>
                    </td>

                    {/* Status */}
                    <td>
                      <StatusBadge status={p.status} />
                    </td>

                    {/* Qualitative Confidence */}
                    <td>
                      <ConfidenceBadge level={p.confidenceLevel} />
                    </td>

                    {/* Missing Data / Conflict Indicator */}
                    <td>
                      {p.conflictFieldsCount > 0 ? (
                        <span
                          style={{
                            color: '#dc2626',
                            fontWeight: 600,
                            fontSize: '0.775rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                          }}
                        >
                          <AlertTriangle size={13} />
                          {p.conflictFieldsCount} Conflicts
                        </span>
                      ) : p.missingFieldsCount > 0 ? (
                        <span style={{ color: '#d97706', fontSize: '0.775rem', fontWeight: 500 }}>
                          {p.missingFieldsCount} Missing
                        </span>
                      ) : (
                        <span style={{ color: '#059669', fontSize: '0.775rem' }}>Complete</span>
                      )}
                    </td>

                    {/* Dynamic Specs Preview */}
                    <td style={{ fontSize: '0.775rem', color: '#64748b', maxWidth: '240px' }}>
                      {specSnippet || (p.description ? p.description.slice(0, 50) + '...' : '—')}
                    </td>

                    {/* 3-Dot Actions Menu */}
                    <td style={{ textAlign: 'right', position: 'relative' }}>
                      <button
                        className="btn-secondary btn-sm"
                        style={{ padding: '4px 6px', borderRadius: '4px' }}
                        onClick={() => setActiveMenuId(activeMenuId === p.id ? null : p.id)}
                      >
                        <MoreVertical size={15} />
                      </button>

                      {/* Dropdown Menu */}
                      {activeMenuId === p.id && (
                        <div
                          style={{
                            position: 'absolute',
                            right: '16px',
                            top: '36px',
                            backgroundColor: '#ffffff',
                            border: '1px solid #e2e8f0',
                            borderRadius: '8px',
                            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                            zIndex: 100,
                            minWidth: '200px',
                            textAlign: 'left',
                            padding: '4px 0',
                          }}
                        >
                          <button
                            style={{
                              width: '100%',
                              padding: '8px 12px',
                              background: 'none',
                              border: 'none',
                              color: '#334155',
                              fontSize: '0.8rem',
                              justifyContent: 'flex-start',
                              borderRadius: 0,
                            }}
                            onClick={() => {
                              setActiveMenuId(null);
                              navigate(`/product-intelligence?id=${p.id}`);
                            }}
                          >
                            <Eye size={14} color="#2563eb" />
                            Open Product Intelligence
                          </button>

                          <button
                            style={{
                              width: '100%',
                              padding: '8px 12px',
                              background: 'none',
                              border: 'none',
                              color: '#334155',
                              fontSize: '0.8rem',
                              justifyContent: 'flex-start',
                              borderRadius: 0,
                            }}
                            onClick={() => {
                              setActiveMenuId(null);
                              navigate(`/validation?productId=${p.id}`);
                            }}
                          >
                            <CheckSquare size={14} color="#d97706" />
                            View Validation Issues
                          </button>

                          <button
                            style={{
                              width: '100%',
                              padding: '8px 12px',
                              background: 'none',
                              border: 'none',
                              color: '#334155',
                              fontSize: '0.8rem',
                              justifyContent: 'flex-start',
                              borderRadius: 0,
                            }}
                            onClick={() => {
                              setActiveMenuId(null);
                              navigate(`/explainability?productId=${p.id}`);
                            }}
                          >
                            <FileSearch size={14} color="#475569" />
                            View Sources & Evidence
                          </button>

                          <button
                            style={{
                              width: '100%',
                              padding: '8px 12px',
                              background: 'none',
                              border: 'none',
                              color: '#334155',
                              fontSize: '0.8rem',
                              justifyContent: 'flex-start',
                              borderRadius: 0,
                            }}
                            onClick={() => handleReprocess(p.id)}
                          >
                            <RotateCw size={14} color="#059669" />
                            Reprocess Intelligence
                          </button>

                          <div style={{ height: '1px', backgroundColor: '#f1f5f9', margin: '4px 0' }} />

                          <button
                            style={{
                              width: '100%',
                              padding: '8px 12px',
                              background: 'none',
                              border: 'none',
                              color: '#dc2626',
                              fontSize: '0.8rem',
                              justifyContent: 'flex-start',
                              borderRadius: 0,
                            }}
                            onClick={() => handleDelete(p.id)}
                          >
                            <Trash2 size={14} color="#dc2626" />
                            Delete Product
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '16px',
          padding: '12px 16px',
          backgroundColor: '#ffffff',
          borderRadius: '8px',
          border: '1px solid #e2e8f0',
        }}
      >
        <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
          Showing page <span style={{ fontWeight: 600, color: '#0f172a' }}>{page}</span> ({products.length} items loaded for {activeTenantName})
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="btn-secondary btn-sm"
            disabled={page <= 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <ChevronLeft size={14} />
            Previous
          </button>
          <button
            className="btn-secondary btn-sm"
            disabled={products.length < pageSize || loading}
            onClick={() => setPage((p) => p + 1)}
            style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            Next
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};

