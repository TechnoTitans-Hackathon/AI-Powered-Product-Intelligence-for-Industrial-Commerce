import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  Globe,
  FileText,
  Layers,
  Sparkles,
  RotateCcw,
  CheckCircle2,
  FileSpreadsheet,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';
import { createProduct, createProductFromUrl, uploadSourceFile, uploadBatchCatalog, submitBatchProcessing, AIProcessingMode } from '../api/client';
import { StageProgressModal } from '../components/StageProgressModal';
import { useTenant } from '../context/TenantContext';

export const UploadProduct: React.FC = () => {
  const navigate = useNavigate();
  const { activeTenantId, activeTenantName } = useTenant();
  const [activeTab, setActiveTab] = useState<'single' | 'url' | 'pdf' | 'batch'>('single');


  // Form states
  const [name, setName] = useState('');
  const [sku, setSku] = useState('');
  const [brand, setBrand] = useState('');
  const [category, setCategory] = useState('Industrial Equipment');
  const [description, setDescription] = useState('');
  const [url, setUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [aiMode, setAiMode] = useState<AIProcessingMode>(AIProcessingMode.AUTO);

  // Processing modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalProductName, setModalProductName] = useState('');
  const [modalProductId, setModalProductId] = useState<string | undefined>(undefined);
  const [currentStep, setCurrentStep] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Batch ingestion result modal
  const [batchResult, setBatchResult] = useState<{
    batch_id: string;
    filename: string;
    total_rows: number;
    imported_count: number;
    skipped_count: number;
    headers_detected: string[];
    errors: string[];
  } | null>(null);
  const [isBatchUploading, setIsBatchUploading] = useState(false);

  const resetForm = () => {
    setName('');
    setSku('');
    setBrand('');
    setCategory('Industrial Equipment');
    setDescription('');
    setUrl('');
    setSelectedFile(null);
    setBatchResult(null);
    setAiMode(AIProcessingMode.AUTO);
  };

  const handleSingleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      setModalProductName(name);
      setIsModalOpen(true);
      setIsCompleted(false);
      setIsFailed(false);
      setCurrentStep(0);

      const prod = await createProduct({
        name,
        sku: sku || undefined,
        brand: brand || undefined,
        category,
        description: description || `Industrial specification for ${name}`,
        ai_mode: aiMode,
      });

      setModalProductId(prod.id);
      setCurrentStep(9);
      setIsCompleted(true);
    } catch (err: any) {
      console.error('Single product creation error:', err);
      setIsFailed(true);
      setErrorMessage(err?.response?.data?.detail || err.message || 'Processing failed');
    }
  };

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    try {
      const prodName = name.trim() || `Product from ${url.split('//')[-1].split('/')[0]}`;
      setModalProductName(prodName);
      setIsModalOpen(true);
      setIsCompleted(false);
      setIsFailed(false);
      setCurrentStep(0);

      const prod = await createProductFromUrl({
        url,
        product_name: name.trim() || undefined,
        sku: sku || undefined,
        category,
        note: description || undefined,
        ai_mode: aiMode,
      });

      setModalProductId(prod.id);
      setCurrentStep(9);
      setIsCompleted(true);
    } catch (err: any) {
      console.error('URL ingestion error:', err);
      setIsFailed(true);
      setErrorMessage(err?.response?.data?.detail || err.message || 'URL ingestion failed');
    }
  };

  const handlePdfSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    try {
      const fileName = selectedFile.name.replace(/\.[^/.]+$/, '');
      const prodName = name.trim() || fileName;
      setModalProductName(prodName);
      setIsModalOpen(true);
      setIsCompleted(false);
      setIsFailed(false);
      setCurrentStep(1);

      // Create product base
      const prod = await createProduct({
        name: prodName,
        sku: sku || undefined,
        category,
        description: description || `Extracted from technical document: ${selectedFile.name}`,
        ai_mode: aiMode,
      });

      setModalProductId(prod.id);
      setCurrentStep(3);

      // Upload and index document
      await uploadSourceFile(selectedFile, prod.id);

      setCurrentStep(9);
      setIsCompleted(true);
    } catch (err: any) {
      console.error('PDF ingestion error:', err);
      setIsFailed(true);
      setErrorMessage(err?.response?.data?.detail || err.message || 'Document processing failed');
    }
  };

  const handleBatchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    try {
      setIsBatchUploading(true);
      const res = await uploadBatchCatalog(selectedFile, true, aiMode);
      setIsBatchUploading(false);
      setBatchResult(res);
    } catch (err: any) {
      setIsBatchUploading(false);
      console.error('Batch upload error:', err);
      alert('Error uploading catalog file: ' + (err?.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="page-body" style={{ maxWidth: '880px' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f172a' }}>Upload & Ingest Product Data</h1>
        <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '4px' }}>
          Provide sparse product descriptions, technical datasheets, URLs, or structured batch files for multi-agent intelligence enrichment.
        </p>
      </div>

      {/* Tabs */}
      <div className="tabs-container">
        <button
          className={`tab-btn ${activeTab === 'single' ? 'active' : ''}`}
          onClick={() => setActiveTab('single')}
        >
          <UploadCloud size={16} />
          Single Product
        </button>
        <button
          className={`tab-btn ${activeTab === 'url' ? 'active' : ''}`}
          onClick={() => setActiveTab('url')}
        >
          <Globe size={16} />
          Product URL
        </button>
        <button
          className={`tab-btn ${activeTab === 'pdf' ? 'active' : ''}`}
          onClick={() => setActiveTab('pdf')}
        >
          <FileText size={16} />
          PDF / Technical Datasheet
        </button>
        <button
          className={`tab-btn ${activeTab === 'batch' ? 'active' : ''}`}
          onClick={() => setActiveTab('batch')}
        >
          <FileSpreadsheet size={16} />
          Batch CSV / XLSX
        </button>
      </div>

      {/* Form Card */}
      <div className="card">
        {/* Tab 1: Single Product */}
        {activeTab === 'single' && (
          <form onSubmit={handleSingleSubmit}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Product Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Diablo 1/2in x 18in Sanding Belt 6pc"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Part Number / SKU / MPN
                </label>
                <input
                  type="text"
                  placeholder="e.g. DCB518ASTS06G"
                  value={sku}
                  onChange={(e) => setSku(e.target.value)}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Brand / Manufacturer
                </label>
                <input
                  type="text"
                  placeholder="e.g. Freud Inc / Diablo"
                  value={brand}
                  onChange={(e) => setBrand(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Category
                </label>
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="Industrial Equipment">Industrial Equipment</option>
                  <option value="Abrasives & Cutting">Abrasives & Cutting</option>
                  <option value="Bearings & Power Transmission">Bearings & Power Transmission</option>
                  <option value="Hydraulics & Fluid Power">Hydraulics & Fluid Power</option>
                  <option value="Motors & Drives">Motors & Drives</option>
                  <option value="Woodworking Machinery">Woodworking Machinery</option>
                  <option value="Electrical Components">Electrical Components</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                Sparse Product Description or Additional Notes
              </label>
              <textarea
                rows={3}
                placeholder="Paste available catalog description, rough specifications, or raw text..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                AI Processing Mode
              </label>
              <select value={aiMode} onChange={(e) => setAiMode(e.target.value as AIProcessingMode)}>
                <option value={AIProcessingMode.AUTO}>Auto (Balanced)</option>
                <option value={AIProcessingMode.FAST}>Fast (Quick extraction)</option>
                <option value={AIProcessingMode.DEEP}>Deep (Comprehensive reasoning)</option>
                <option value={AIProcessingMode.LOCAL}>Local (Strict local-only privacy)</option>
              </select>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                Optional Technical Document (PDF, Image, Text)
              </label>
              <input
                type="file"
                accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.txt,.csv,.xlsx"
                onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                style={{ fontSize: '0.825rem' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button type="button" className="btn-secondary" onClick={resetForm}>
                <RotateCcw size={15} />
                Reset
              </button>
              <button type="submit" className="btn-primary">
                <Sparkles size={15} />
                Process Product
              </button>
            </div>
          </form>
        )}

        {/* Tab 2: Product URL */}
        {activeTab === 'url' && (
          <form onSubmit={handleUrlSubmit}>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                Product Web URL *
              </label>
              <input
                type="url"
                required
                placeholder="https://www.industrial-supplier.com/products/bearing-6205"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
              <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
                The AI ingestion agent will scrape, extract, and normalize specifications from this web source.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Product Name (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Auto-inferred if blank"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Target Category
                </label>
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="Industrial Equipment">Industrial Equipment</option>
                  <option value="Abrasives & Cutting">Abrasives & Cutting</option>
                  <option value="Bearings & Power Transmission">Bearings & Power Transmission</option>
                  <option value="Hydraulics & Fluid Power">Hydraulics & Fluid Power</option>
                  <option value="Motors & Drives">Motors & Drives</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                AI Processing Mode
              </label>
              <select value={aiMode} onChange={(e) => setAiMode(e.target.value as AIProcessingMode)}>
                <option value={AIProcessingMode.AUTO}>Auto (Balanced)</option>
                <option value={AIProcessingMode.FAST}>Fast (Quick extraction)</option>
                <option value={AIProcessingMode.DEEP}>Deep (Comprehensive reasoning)</option>
                <option value={AIProcessingMode.LOCAL}>Local (Strict local-only privacy)</option>
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
              <button type="button" className="btn-secondary" onClick={resetForm}>
                <RotateCcw size={15} />
                Reset
              </button>
              <button type="submit" className="btn-primary">
                <Globe size={15} />
                Ingest & Process URL
              </button>
            </div>
          </form>
        )}

        {/* Tab 3: PDF Document */}
        {activeTab === 'pdf' && (
          <form onSubmit={handlePdfSubmit}>
            <div
              style={{
                border: '2px dashed #cbd5e1',
                borderRadius: '8px',
                padding: '36px 20px',
                textAlign: 'center',
                backgroundColor: '#f8fafc',
                marginBottom: '20px',
              }}
            >
              <FileText size={36} color="#64748b" style={{ margin: '0 auto 12px auto' }} />
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#1e293b' }}>
                Upload Technical Datasheet or PDF Catalog
              </div>
              <p style={{ fontSize: '0.785rem', color: '#64748b', marginTop: '4px', marginBottom: '16px' }}>
                Supports PDF, Word Documents, and Technical manuals up to 50MB
              </p>
              <input
                type="file"
                required
                accept=".pdf,.doc,.docx"
                onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                style={{ maxWidth: '320px' }}
              />
              {selectedFile && (
                <div style={{ marginTop: '12px', fontSize: '0.825rem', color: '#059669', fontWeight: 600 }}>
                  Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                </div>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Product / Item Name (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Defaults to filename"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Category
                </label>
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="Industrial Equipment">Industrial Equipment</option>
                  <option value="Abrasives & Cutting">Abrasives & Cutting</option>
                  <option value="Bearings & Power Transmission">Bearings & Power Transmission</option>
                  <option value="Hydraulics & Fluid Power">Hydraulics & Fluid Power</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                AI Processing Mode
              </label>
              <select value={aiMode} onChange={(e) => setAiMode(e.target.value as AIProcessingMode)}>
                <option value={AIProcessingMode.AUTO}>Auto (Balanced)</option>
                <option value={AIProcessingMode.FAST}>Fast (Quick extraction)</option>
                <option value={AIProcessingMode.DEEP}>Deep (Comprehensive reasoning)</option>
                <option value={AIProcessingMode.LOCAL}>Local (Strict local-only privacy)</option>
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button type="button" className="btn-secondary" onClick={resetForm}>
                <RotateCcw size={15} />
                Reset
              </button>
              <button type="submit" className="btn-primary" disabled={!selectedFile}>
                <FileText size={15} />
                Process Document
              </button>
            </div>
          </form>
        )}

        {/* Tab 4: Batch CSV / XLSX */}
        {activeTab === 'batch' && (
          <form onSubmit={handleBatchSubmit}>
            <div
              style={{
                border: '2px dashed #cbd5e1',
                borderRadius: '8px',
                padding: '36px 20px',
                textAlign: 'center',
                backgroundColor: '#f8fafc',
                marginBottom: '20px',
              }}
            >
              <FileSpreadsheet size={36} color="#64748b" style={{ margin: '0 auto 12px auto' }} />
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#1e293b' }}>
                Upload Structured Batch Catalog (CSV or XLSX)
              </div>
              <p style={{ fontSize: '0.785rem', color: '#64748b', marginTop: '4px', marginBottom: '16px' }}>
                Accepts official UniHack format (`Mfg_Part_Num`, `Part_Desc`, `Brand`, `Manufacturer`) or generic product spreadsheets.
              </p>
              <input
                type="file"
                required
                accept=".csv,.xlsx,.xls"
                onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                style={{ maxWidth: '320px' }}
              />
              {selectedFile && (
                <div style={{ marginTop: '12px', fontSize: '0.825rem', color: '#059669', fontWeight: 600 }}>
                  Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                </div>
              )}
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                AI Processing Mode
              </label>
              <select value={aiMode} onChange={(e) => setAiMode(e.target.value as AIProcessingMode)}>
                <option value={AIProcessingMode.AUTO}>Auto (Balanced)</option>
                <option value={AIProcessingMode.FAST}>Fast (Quick extraction)</option>
                <option value={AIProcessingMode.DEEP}>Deep (Comprehensive reasoning)</option>
                <option value={AIProcessingMode.LOCAL}>Local (Strict local-only privacy)</option>
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button type="button" className="btn-secondary" onClick={resetForm}>
                <RotateCcw size={15} />
                Reset
              </button>
              <button type="submit" className="btn-primary" disabled={!selectedFile}>
                <Layers size={15} />
                Submit Batch Job
              </button>
            </div>
          </form>
        )}
      </div>

      {/* AI Processing Screen Modal */}
      <StageProgressModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        productName={modalProductName}
        productId={modalProductId}
        isCompleted={isCompleted}
        isFailed={isFailed}
        errorMessage={errorMessage}
        currentStepIndex={currentStep}
      />

      {/* Batch Ingestion Result Modal */}
      {batchResult && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '520px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  backgroundColor: '#ecfdf5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#059669',
                }}
              >
                <CheckCircle2 size={22} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#0f172a' }}>Batch Ingestion Successful</h3>
                <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  File: <strong>{batchResult.filename}</strong> (Batch ID: {batchResult.batch_id})
                </p>
              </div>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '12px',
                marginBottom: '16px',
                padding: '12px',
                backgroundColor: '#f8fafc',
                borderRadius: '6px',
              }}
            >
              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Total Rows Detected</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>
                  {batchResult.total_rows}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Products Created</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#059669' }}>
                  {batchResult.imported_count}
                </div>
              </div>
              {batchResult.skipped_count > 0 && (
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Skipped Rows</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#d97706' }}>
                    {batchResult.skipped_count}
                  </div>
                </div>
              )}
            </div>

            <p style={{ fontSize: '0.825rem', color: '#334155', marginBottom: '20px' }}>
              All <strong>{batchResult.imported_count}</strong> product records have been created in the catalog. Background multi-agent AI intelligence enrichment jobs are now executing.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn-secondary"
                onClick={() => {
                  setBatchResult(null);
                  navigate('/catalog');
                }}
              >
                Go to Catalog
              </button>
              <button
                className="btn-primary"
                onClick={() => {
                  setBatchResult(null);
                  navigate('/batch-processing');
                }}
              >
                View Batch Progress <ArrowRight size={15} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
