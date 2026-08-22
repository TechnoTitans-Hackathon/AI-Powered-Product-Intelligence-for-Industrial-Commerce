import React from 'react';
import { CheckCircle2, Loader2, AlertCircle, Sparkles, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface Props {
  isOpen: boolean;
  onClose?: () => void;
  productName: string;
  jobId?: string;
  productId?: string;
  isCompleted: boolean;
  isFailed?: boolean;
  errorMessage?: string;
  currentStepIndex?: number;
}

const PIPELINE_STAGES = [
  { id: 'input', label: '1. Reading Input & Multimodal Ingestion', desc: 'Parsing raw text, URLs, documents, and structured inputs' },
  { id: 'discovery', label: '2. Product Identity Discovery', desc: 'Discovery Agent identifying part numbers, brand, and category' },
  { id: 'retrieval', label: '3. Evidence Retrieval', desc: 'Assembling local knowledge corpus snippets and datasheets' },
  { id: 'decision', label: '4. Knowledge Decision Engine', desc: 'Evaluating evidence sufficiency with adaptive loop control' },
  { id: 'research', label: '5. Targeted Research & Acquisition', desc: 'Acquiring missing technical data from verified industrial sources' },
  { id: 'intelligence', label: '6. Multi-Agent Intelligence Extraction', desc: 'Intelligence Agent extracting specifications and features' },
  { id: 'normalize', label: '7. Attribute & Unit Normalization', desc: 'Converting fractions, decimals, and standardizing UOMs' },
  { id: 'validate', label: '8. Deterministic Validation', desc: 'Executing official validation checks and anomaly detection' },
  { id: 'confidence', label: '9. Mathematical Confidence Scoring', desc: 'Computing field-level and overall qualitative confidence' },
  { id: 'output', label: '10. Commerce-Ready Structuring', desc: 'Formatting 252-column schema with full explainability provenance' },
];

export const StageProgressModal: React.FC<Props> = ({
  isOpen,
  onClose,
  productName,
  productId,
  isCompleted,
  isFailed,
  errorMessage,
  currentStepIndex = 9,
}) => {
  const navigate = useNavigate();

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '640px' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: isFailed ? '#fee2e2' : isCompleted ? '#dcfce7' : '#eff6ff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: isFailed ? '#dc2626' : isCompleted ? '#16a34a' : '#2563eb',
            }}
          >
            {isFailed ? <AlertCircle size={20} /> : isCompleted ? <CheckCircle2 size={20} /> : <Sparkles size={20} />}
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', color: '#0f172a' }}>
              {isFailed ? 'Processing Encountered an Issue' : isCompleted ? 'Product Intelligence Generated' : 'AI Multi-Agent Pipeline Running'}
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#64748b' }}>{productName}</p>
          </div>
        </div>

        {isFailed && errorMessage && (
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '6px',
              color: '#991b1b',
              fontSize: '0.85rem',
              marginBottom: '16px',
            }}
          >
            {errorMessage}
          </div>
        )}

        {/* Stage List */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            margin: '20px 0',
            maxHeight: '340px',
            overflowY: 'auto',
            paddingRight: '6px',
          }}
        >
          {PIPELINE_STAGES.map((stage, idx) => {
            const isStageDone = isCompleted || idx < currentStepIndex;
            const isStageActive = !isCompleted && !isFailed && idx === currentStepIndex;

            return (
              <div
                key={stage.id}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  backgroundColor: isStageActive ? '#f0fdf4' : isStageDone ? '#f8fafc' : '#ffffff',
                  border: isStageActive ? '1px solid #86efac' : '1px solid #f1f5f9',
                }}
              >
                <div style={{ marginTop: '2px', flexShrink: 0 }}>
                  {isStageDone ? (
                    <CheckCircle2 size={16} color="#16a34a" />
                  ) : isStageActive ? (
                    <Loader2 size={16} color="#2563eb" style={{ animation: 'spin 1s linear infinite' }} />
                  ) : (
                    <div
                      style={{
                        width: '14px',
                        height: '14px',
                        borderRadius: '50%',
                        border: '2px solid #cbd5e1',
                        margin: '1px',
                      }}
                    />
                  )}
                </div>

                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontSize: '0.85rem',
                      fontWeight: isStageActive || isStageDone ? 600 : 400,
                      color: isStageActive ? '#15803d' : isStageDone ? '#0f172a' : '#94a3b8',
                    }}
                  >
                    {stage.label}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: isStageActive ? '#166534' : '#64748b' }}>{stage.desc}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
          {onClose && (
            <button className="btn-secondary" onClick={onClose}>
              {isCompleted ? 'Close' : 'Run in Background'}
            </button>
          )}
          {isCompleted && productId && (
            <button
              className="btn-primary"
              onClick={() => {
                if (onClose) onClose();
                navigate(`/product-intelligence?id=${productId}`);
              }}
            >
              View Product Intelligence
              <ArrowRight size={15} />
            </button>
          )}
        </div>
      </div>
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
