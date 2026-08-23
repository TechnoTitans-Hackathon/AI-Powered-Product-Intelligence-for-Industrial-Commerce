import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Cpu,
  Layers,
  FileText,
  ShieldCheck,
  AlertTriangle,
  RotateCw,
  ArrowLeft,
  Search,
  ExternalLink,
  CheckCircle2,
  Table,
  CheckSquare,
} from 'lucide-react';
import { getProductById, getProducts, triggerProductReprocess, exportProductXlsx, AIProcessingMode } from '../api/client';
import { ProductItem, DynamicAttribute } from '../types';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { StatusBadge } from '../components/StatusBadge';
import { useTenant } from '../context/TenantContext';


export const ProductIntelligence: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { activeTenantId, activeTenantName } = useTenant();
  const productId = searchParams.get('id');

  const [product, setProduct] = useState<ProductItem | null>(null);
  const [allProducts, setAllProducts] = useState<ProductItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [reprocessing, setReprocessing] = useState(false);
  const [aiMode, setAiMode] = useState<AIProcessingMode>(AIProcessingMode.AUTO);
  const [activeTab, setActiveTab] = useState<'overview' | 'specs' | 'features' | 'descriptions' | 'evidence' | 'commerce'>('overview');

  const loadProduct = async (id: string) => {
    try {
      setLoading(true);
      const data = await getProductById(id);
      setProduct(data);
    } catch (err) {
      console.error('Error fetching product intelligence:', err);
      setProduct(null);
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
        if (productId && prods.some(p => p.id === productId)) {
          await loadProduct(productId);
        } else if (prods.length > 0) {
          setSearchParams({ id: prods[0].id });
          await loadProduct(prods[0].id);
        } else {
          setProduct(null);
        }
      } catch (err) {
        console.error('Initialization error:', err);
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
  }, [productId, activeTenantId]);

  const handleReprocess = async () => {
    if (!product) return;
    try {
      setReprocessing(true);
      await triggerProductReprocess(product.id, aiMode);
      await loadProduct(product.id);
    } catch (err) {
      console.error('Reprocess error:', err);
    } finally {
      setReprocessing(false);
    }
  };

  if (loading && !product) {
    return (
      <div className="page-body" style={{ textAlign: 'center', padding: '60px' }}>
        <p style={{ color: '#64748b' }}>Loading Product Intelligence for {activeTenantName}...</p>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="page-body">
        <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
          <p style={{ color: '#64748b', fontSize: '1rem', marginBottom: '8px' }}>
            No products found in <strong>{activeTenantName}</strong> workspace.
          </p>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '16px' }}>
            Ingest a product or upload a catalog to view AI multi-agent intelligence results.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '10px' }}>
            <button className="btn-primary" onClick={() => navigate('/upload')}>
              Upload Product
            </button>
            <button className="btn-secondary" onClick={() => navigate('/catalog')}>
              Go to Catalog
            </button>
          </div>
        </div>
      </div>
    );
  }


  return (
    <div className="page-body">
      {/* Top Breadcrumb & Product Selector */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}
      >
        <button
          className="btn-secondary btn-sm"
          onClick={() => navigate('/catalog')}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <ArrowLeft size={14} />
          Back to Catalog
        </button>

        {/* Product Switcher Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Switch Product:</span>
          <select
            value={product.id}
            onChange={(e) => {
              setSearchParams({ id: e.target.value });
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

      {/* Main Product Header Card */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ flex: 1, minWidth: '320px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <span
                style={{
                  fontFamily: 'monospace',
                  fontSize: '0.825rem',
                  backgroundColor: '#f1f5f9',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  color: '#1e293b',
                  fontWeight: 600,
                }}
              >
                {product.mpn || product.sku}
              </span>
              <StatusBadge status={product.status} />
              <ConfidenceBadge level={product.confidenceLevel} />
            </div>

            <h1 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' }}>{product.name}</h1>

            <div style={{ display: 'flex', gap: '16px', marginTop: '6px', fontSize: '0.825rem', color: '#475569' }}>
              <span>
                Brand: <strong style={{ color: '#0f172a' }}>{product.brand}</strong>
              </span>
              <span>
                Manufacturer: <strong style={{ color: '#0f172a' }}>{product.commerceData?.MANUFACTURER_NAME || product.intelligence?.manufacturer?.value || product.manufacturer || 'Unknown'}</strong>
              </span>
              <span>
                Category: <strong style={{ color: '#0f172a' }}>{product.category}</strong>
              </span>
              <span>
                Industry: <strong style={{ color: '#0f172a' }}>{product.industry || 'Industrial'}</strong>
              </span>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button className="btn-secondary" onClick={async () => {
              try {
                await exportProductXlsx(product.id);
              } catch (err: any) {
                alert(err.message || "Export failed.");
              }
            }}>
              <FileText size={14} color="#059669" />
              Download Excel
            </button>
            <button className="btn-secondary" onClick={() => navigate(`/validation?productId=${product.id}`)}>
              <CheckSquare size={14} color="#d97706" />
              Validation Issues ({product.validationIssues?.length || 0})
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', borderLeft: '1px solid #e2e8f0', paddingLeft: '8px' }}>
              <select
                value={aiMode}
                onChange={(e) => setAiMode(e.target.value as AIProcessingMode)}
                style={{ fontSize: '0.8rem', padding: '4px 8px', height: '32px' }}
                disabled={reprocessing}
              >
                <option value={AIProcessingMode.AUTO}>Auto</option>
                <option value={AIProcessingMode.FAST}>Fast</option>
                <option value={AIProcessingMode.DEEP}>Deep</option>
                <option value={AIProcessingMode.LOCAL}>Local</option>
              </select>
              <button className="btn-primary" onClick={handleReprocess} disabled={reprocessing} style={{ height: '32px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <RotateCw size={14} className={reprocessing ? 'animate-spin' : ''} />
                Reprocess
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Intelligence Tabs */}
      <div className="tabs-container">
        <button
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <Cpu size={15} />
          Overview & Metrics
        </button>
        <button
          className={`tab-btn ${activeTab === 'specs' ? 'active' : ''}`}
          onClick={() => setActiveTab('specs')}
        >
          <Table size={15} />
          Dynamic Specifications ({product.dynamicAttributes?.length || 0})
        </button>
        <button
          className={`tab-btn ${activeTab === 'features' ? 'active' : ''}`}
          onClick={() => setActiveTab('features')}
        >
          <Layers size={15} />
          Features & Applications
        </button>
        <button
          className={`tab-btn ${activeTab === 'descriptions' ? 'active' : ''}`}
          onClick={() => setActiveTab('descriptions')}
        >
          <FileText size={15} />
          Descriptions & Taxonomy
        </button>
        <button
          className={`tab-btn ${activeTab === 'evidence' ? 'active' : ''}`}
          onClick={() => setActiveTab('evidence')}
        >
          <Search size={15} />
          Sources & Evidence
        </button>
        <button
          className={`tab-btn ${activeTab === 'commerce' ? 'active' : ''}`}
          onClick={() => setActiveTab('commerce')}
        >
          <Table size={15} />
          Commerce 252-Col Schema
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
          <div>
            <div className="card">
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
                AI-Generated Product Summary
              </h3>
              <p style={{ fontSize: '0.875rem', color: '#334155', lineHeight: 1.6 }}>
                {product.description || 'No summary generated.'}
              </p>
            </div>

            {/* Conflicts Warning Banner if any */}
            {product.conflictFieldsCount > 0 && (
              <div
                style={{
                  backgroundColor: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '20px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#991b1b', fontWeight: 600 }}>
                  <AlertTriangle size={18} />
                  Conflicting Information Detected ({product.conflictFieldsCount} fields)
                </div>
                <p style={{ fontSize: '0.8rem', color: '#b91c1c', marginTop: '4px' }}>
                  Multiple industrial sources disagree on specifications for this product. Inspect the Validation Center or Explainability tab for source comparison.
                </p>
              </div>
            )}

            {/* Quick Specs Highlight Card */}
            <div className="card">
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px' }}>
                Key Technical Attributes
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                {(product.dynamicAttributes || [])
                  .filter((a) => a.key !== 'feature')
                  .slice(0, 8)
                  .map((attr, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '6px',
                        backgroundColor: '#f8fafc',
                        border: '1px solid #f1f5f9',
                      }}
                    >
                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{attr.key}</div>
                      <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#0f172a', marginTop: '2px' }}>
                        {attr.value ? `${attr.value}${attr.unit ? ' ' + attr.unit : ''}` : <span style={{ color: '#d97706', fontStyle: 'italic' }}>MISSING</span>}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          {/* Right Column: Intelligence Metrics */}
          <div>
            <div className="card">
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px' }}>
                Intelligence Scorecard
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                    <span style={{ color: '#64748b' }}>Qualitative Confidence</span>
                    <ConfidenceBadge level={product.confidenceLevel} />
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                    <span style={{ color: '#64748b' }}>Populated Attributes</span>
                    <strong style={{ color: '#0f172a' }}>{product.fieldsPopulated || 0} fields</strong>
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                    <span style={{ color: '#64748b' }}>Missing Information</span>
                    <span style={{ color: product.missingFieldsCount > 0 ? '#d97706' : '#059669', fontWeight: 600 }}>
                      {product.missingFieldsCount} fields
                    </span>
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                    <span style={{ color: '#64748b' }}>Source Conflicts</span>
                    <span style={{ color: product.conflictFieldsCount > 0 ? '#dc2626' : '#059669', fontWeight: 600 }}>
                      {product.conflictFieldsCount} detected
                    </span>
                  </div>
                </div>

                <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '12px' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    Pipeline status: <strong style={{ color: '#334155' }}>{product.status.toUpperCase()}</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Dynamic Specifications */}
      {activeTab === 'specs' && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Dynamic Product Specifications</h3>
              <p style={{ fontSize: '0.785rem', color: '#64748b', marginTop: '2px' }}>
                Extracted and normalized attributes with field-level evidence status
              </p>
            </div>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Specification Key</th>
                  <th>Current / Normalized Value</th>
                  <th>Unit</th>
                  <th>Field Status</th>
                  <th>Confidence</th>
                  <th>Source Provenance Snippet</th>
                </tr>
              </thead>
              <tbody>
                {(product.dynamicAttributes || []).length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: '#94a3b8' }}>
                      No dynamic specifications recorded.
                    </td>
                  </tr>
                ) : (
                  (product.dynamicAttributes || []).map((attr, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600, color: '#0f172a' }}>{attr.key}</td>
                      <td>
                        {attr.value ? (
                          <span style={{ color: '#0f172a', fontWeight: 500 }}>{attr.value}</span>
                        ) : (
                          <span style={{ color: '#d97706', fontStyle: 'italic', fontWeight: 500 }}>MISSING</span>
                        )}
                      </td>
                      <td style={{ color: '#64748b', fontSize: '0.8rem' }}>{attr.unit || '—'}</td>
                      <td>
                        <span
                          style={{
                            fontSize: '0.725rem',
                            fontWeight: 600,
                            padding: '2px 6px',
                            borderRadius: '4px',
                            backgroundColor:
                              attr.fieldStatus === 'DIRECTLY_SUPPORTED'
                                ? '#ecfdf5'
                                : attr.fieldStatus === 'INFERRED'
                                ? '#eff6ff'
                                : attr.fieldStatus === 'CONFLICTING'
                                ? '#fef2f2'
                                : '#fffbeb',
                            color:
                              attr.fieldStatus === 'DIRECTLY_SUPPORTED'
                                ? '#065f46'
                                : attr.fieldStatus === 'INFERRED'
                                ? '#1e40af'
                                : attr.fieldStatus === 'CONFLICTING'
                                ? '#991b1b'
                                : '#92400e',
                          }}
                        >
                          {attr.fieldStatus || 'SUPPORTED'}
                        </span>
                      </td>
                      <td>
                        <ConfidenceBadge level={attr.confidenceLevel} />
                      </td>
                      <td style={{ fontSize: '0.785rem', color: '#475569', maxWidth: '300px' }}>
                        {attr.sourceSnippet ? (
                          <span title={attr.sourceSnippet}>
                            "{attr.sourceSnippet.slice(0, 80)}..."
                          </span>
                        ) : (
                          <span style={{ color: '#94a3b8' }}>—</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Features & Applications */}
      {activeTab === 'features' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div className="card">
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f172a', marginBottom: '14px' }}>
              Extracted Product Features
            </h3>
            {(product.features || []).length === 0 ? (
              <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No item features extracted.</p>
            ) : (
              <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.875rem', color: '#334155' }}>
                {(product.features || []).map((feat, idx) => (
                  <li key={idx}>{feat.value || feat}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="card">
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f172a', marginBottom: '14px' }}>
              Industrial Applications & Standards
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <div style={{ fontSize: '0.785rem', fontWeight: 600, color: '#64748b' }}>Applications</div>
                <div style={{ fontSize: '0.875rem', color: '#0f172a', marginTop: '2px' }}>
                  {product.applications && product.applications.length > 0
                    ? product.applications.map((a) => a.value || a).join(', ')
                    : `Suitable for heavy-duty ${product.category?.toLowerCase() || 'industrial'} applications.`}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.785rem', fontWeight: 600, color: '#64748b' }}>Industry Sector</div>
                <div style={{ fontSize: '0.875rem', color: '#0f172a', marginTop: '2px' }}>
                  {product.industry || 'General Industrial Manufacturing'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Descriptions & Taxonomy */}
      {activeTab === 'descriptions' && (
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#0f172a', marginBottom: '16px' }}>
            Structured Commerce Descriptions
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b' }}>Short Description (SHORT_DESC)</div>
              <div style={{ fontSize: '0.875rem', color: '#0f172a', marginTop: '4px', padding: '10px 12px', backgroundColor: '#f8fafc', borderRadius: '6px', border: '1px solid #f1f5f9' }}>
                {product.description}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b' }}>Long Description (LONG_DESC1)</div>
              <div style={{ fontSize: '0.875rem', color: '#0f172a', marginTop: '4px', padding: '10px 12px', backgroundColor: '#f8fafc', borderRadius: '6px', border: '1px solid #f1f5f9' }}>
                {product.intelligence?.long_description?.value || product.description}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b' }}>Marketing Description</div>
              <div style={{ fontSize: '0.875rem', color: '#0f172a', marginTop: '4px', padding: '10px 12px', backgroundColor: '#f8fafc', borderRadius: '6px', border: '1px solid #f1f5f9' }}>
                {product.intelligence?.marketing_description?.value || 'Industrial grade performance engineered for demanding environments.'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Sources & Evidence */}
      {activeTab === 'evidence' && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Source Documents & Evidence</h3>
              <p style={{ fontSize: '0.785rem', color: '#64748b', marginTop: '2px' }}>
                Primary datasheets and corpus snippets used to extract this product's intelligence
              </p>
            </div>
            <button className="btn-secondary btn-sm" onClick={() => navigate(`/explainability?productId=${product.id}`)}>
              Full Explainability View
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {product.sourceDocument ? (
              <div style={{ padding: '12px', borderRadius: '6px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                <div style={{ fontWeight: 600, color: '#0f172a' }}>{product.sourceDocument.name}</div>
                <div style={{ fontSize: '0.785rem', color: '#64748b', marginTop: '2px' }}>
                  Type: {product.sourceDocument.type} • Pages: {product.sourceDocument.pages} • OCR Accuracy: {product.sourceDocument.ocrAccuracy}%
                </div>
              </div>
            ) : (
              <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                Knowledge derived from baseline industrial catalog corpus.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Tab 6: Commerce 252-Column Schema Mapping */}
      {activeTab === 'commerce' && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Official Commerce Output Data (252 Columns)</h3>
              <p style={{ fontSize: '0.785rem', color: '#64748b', marginTop: '2px' }}>
                Official expected-output schema format for ecommerce catalogs
              </p>
            </div>
          </div>

          <div className="table-container" style={{ maxHeight: '420px', overflowY: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Column Name</th>
                  <th>Mapped Value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(product.commerceData || {}).length === 0 ? (
                  <tr>
                    <td colSpan={2} style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
                      Commerce data mapping is generated during pipeline execution.
                    </td>
                  </tr>
                ) : (
                  Object.entries(product.commerceData || {}).map(([key, val], idx) => (
                    <tr key={idx}>
                      <td style={{ fontFamily: 'monospace', fontWeight: 600, color: '#1e3a8a', fontSize: '0.8rem' }}>
                        {key}
                      </td>
                      <td style={{ color: '#0f172a', fontSize: '0.825rem' }}>
                        {val ? String(val) : <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>null</span>}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
