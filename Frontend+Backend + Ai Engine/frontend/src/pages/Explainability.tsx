import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  FileSearch,
  FileText,
  Search,
  ShieldCheck,
  ExternalLink,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { getExplainability, getProducts } from '../api/client';
import { ProductItem, SourceDoc, EvidenceItem } from '../types';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { useTenant } from '../context/TenantContext';

export const Explainability: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { activeTenantId, activeTenantName } = useTenant();
  const filterProductId = searchParams.get('productId');

  const [explainData, setExplainData] = useState<{
    product_id: string;
    product_name: string;
    sources: SourceDoc[];
    evidence: EvidenceItem[];
    field_provenance: any[];
    overall_confidence: number;
    confidence_level: string;
    missing_fields_count: number;
    conflict_fields_count: number;
  } | null>(null);

  const [allProducts, setAllProducts] = useState<ProductItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSnippet, setSelectedSnippet] = useState<string | null>(null);

  const loadData = async (pId: string) => {
    try {
      setLoading(true);
      const data = await getExplainability(pId);
      setExplainData(data);
      if (data.evidence && data.evidence.length > 0) {
        setSelectedSnippet(data.evidence[0].content);
      }
    } catch (err) {
      console.error('Error fetching explainability data:', err);
      setExplainData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        const prods = await getProducts({ limit: 50 });
        setAllProducts(prods);
        if (filterProductId && prods.some(p => p.id === filterProductId)) {
          await loadData(filterProductId);
        } else if (prods.length > 0) {
          setSearchParams({ productId: prods[0].id });
          await loadData(prods[0].id);
        } else {
          setExplainData(null);
        }
      } catch (err) {
        console.error('Explainability init error:', err);
      } finally {
        setLoading(false);
      }
    };
    init();

    const handleTenantChange = () => {
      init();
    };
    window.addEventListener('tenant-changed', handleTenantChange);
    return () => {
      window.removeEventListener('tenant-changed', handleTenantChange);
    };
  }, [filterProductId, activeTenantId]);


  return (
    <div className="page-body">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f172a' }}>Source Explainability & Provenance</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '2px' }}>
            Inspect full provenance chains, supporting document snippets, and reasoning for every AI-extracted specification.
          </p>
        </div>

        {/* Product selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Select Product:</span>
          <select
            value={explainData?.product_id || ''}
            onChange={(e) => {
              setSearchParams({ productId: e.target.value });
            }}
            style={{ width: '280px', fontSize: '0.8rem' }}
          >
            {allProducts.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.mpn || p.sku})
              </option>
            ))}
          </select>
        </div>
      </div>

      {explainData && (
        <>
          {/* Top Status Card */}
          <div className="card" style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <h2 style={{ fontSize: '1.15rem', fontWeight: 600, color: '#0f172a' }}>{explainData.product_name}</h2>
                  <ConfidenceBadge level={explainData.confidence_level} />
                </div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  Product ID: <span style={{ fontFamily: 'monospace' }}>{explainData.product_id}</span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '24px' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Sources Consulted</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>
                    {explainData.sources.length}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Evidence Chunks</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>
                    {explainData.evidence.length}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Missing Specs</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: explainData.missing_fields_count > 0 ? '#d97706' : '#059669' }}>
                    {explainData.missing_fields_count}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Dual Panel: Field Provenance Table (Left) + Evidence Viewer (Right) */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '20px', alignItems: 'start' }}>
            {/* Left Panel: Field-Level Provenance Mapping */}
            <div className="card">
              <div className="card-header">
                <div>
                  <h3 className="card-title">Field-Level Grounding & Discrepancies</h3>
                  <p style={{ fontSize: '0.785rem', color: '#64748b', marginTop: '2px' }}>
                    Multi-agent consensus, conflict detection, and verification status per attribute
                  </p>
                </div>
              </div>

              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Attribute Key</th>
                      <th>Resolved Value</th>
                      <th>Grounding Status</th>
                      <th>Confidence</th>
                      <th>Evidence Snippets</th>
                    </tr>
                  </thead>
                  <tbody>
                    {explainData.field_provenance.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
                          No field provenance recorded for this product.
                        </td>
                      </tr>
                    ) : (
                      explainData.field_provenance.map((f, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600, color: '#0f172a' }}>{f.field_name}</td>
                          <td>
                            {f.value ? (
                              <span style={{ color: '#0f172a', fontWeight: 500 }}>{f.value}</span>
                            ) : (
                              <span style={{ color: '#d97706', fontStyle: 'italic', fontSize: '0.8rem' }}>MISSING</span>
                            )}
                          </td>
                          <td>
                            {f.has_conflict ? (
                              <span
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  color: '#dc2626',
                                  fontSize: '0.75rem',
                                  fontWeight: 600,
                                }}
                              >
                                <AlertTriangle size={12} />
                                CONFLICT
                              </span>
                            ) : f.status === 'DIRECTLY_SUPPORTED' ? (
                              <span
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  color: '#059669',
                                  fontSize: '0.75rem',
                                  fontWeight: 600,
                                }}
                              >
                                <CheckCircle2 size={12} />
                                SUPPORTED
                              </span>
                            ) : (
                              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>{f.status}</span>
                            )}
                          </td>
                          <td>
                            <ConfidenceBadge level={f.confidence >= 0.8 ? 'HIGH' : f.confidence >= 0.5 ? 'MEDIUM' : 'LOW'} />
                          </td>
                          <td>
                            {f.supporting_sources && f.supporting_sources.length > 0 ? (
                              <button
                                className="btn-secondary btn-sm"
                                style={{ fontSize: '0.725rem', padding: '2px 8px' }}
                                onClick={() => setSelectedSnippet(f.supporting_sources[0].snippet)}
                              >
                                View ({f.evidence_count})
                              </button>
                            ) : (
                              <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>None</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Right Panel: Source Documents & Datasheet Text Viewer */}
            <div className="card">
              <div className="card-header">
                <div>
                  <h3 className="card-title">Document Citations & Evidence</h3>
                  <p style={{ fontSize: '0.785rem', color: '#64748b', marginTop: '2px' }}>
                    Uploaded datasheets, PDFs, and scraped URLs
                  </p>
                </div>
              </div>

              {/* Source Documents List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                {explainData.sources.length === 0 ? (
                  <div style={{ color: '#94a3b8', fontSize: '0.8rem', padding: '12px', textAlign: 'center' }}>
                    No source documents attached to this product yet.
                  </div>
                ) : (
                  explainData.sources.map((sd) => (
                    <div
                      key={sd.id}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '6px',
                        backgroundColor: '#f8fafc',
                        border: '1px solid #e2e8f0',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                      }}
                    >
                      <FileText size={16} color="#2563eb" />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#0f172a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {sd.name}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                          Type: {sd.type} {sd.fileSize ? `• ${sd.fileSize}` : ''}
                        </div>

                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Active Raw Snippet Box */}
              <div>
                <div style={{ fontSize: '0.785rem', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
                  Datasheet Text Snippet
                </div>
                <div
                  style={{
                    padding: '14px',
                    borderRadius: '6px',
                    backgroundColor: '#0f172a',
                    color: '#f8fafc',
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '0.785rem',
                    lineHeight: 1.6,
                    maxHeight: '320px',
                    overflowY: 'auto',
                    border: '1px solid #1e293b',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {selectedSnippet || (explainData.evidence.length > 0 ? explainData.evidence[0].content : 'No snippet text selected.')}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {!explainData && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
          <p style={{ color: '#64748b', fontSize: '1rem', marginBottom: '8px' }}>
            No products found in <strong>{activeTenantName}</strong> workspace.
          </p>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '16px' }}>
            Upload or ingest a product to inspect provenance chains and citations.
          </p>
          <button className="btn-primary" onClick={() => navigate('/upload')}>
            Upload Product
          </button>
        </div>
      )}
    </div>
  );
};
