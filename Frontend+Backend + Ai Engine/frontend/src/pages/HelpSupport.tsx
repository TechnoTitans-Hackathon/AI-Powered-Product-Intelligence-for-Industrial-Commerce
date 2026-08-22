import React from 'react';
import { HelpCircle, BookOpen, ShieldCheck, Cpu, Layers } from 'lucide-react';

export const HelpSupport: React.FC = () => {
  return (
    <div className="page-body" style={{ maxWidth: '900px' }}>
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f172a' }}>Platform Guide & Documentation</h1>
        <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '2px' }}>
          Understanding the multi-agent AI pipeline, qualitative confidence calculations, and industrial commerce schema
        </p>
      </div>

      {/* 10-Stage Pipeline Overview */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={18} color="#2563eb" />
            <h2 className="card-title">10-Stage Multi-Agent Architecture</h2>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.85rem', color: '#334155' }}>
          <div>
            <strong>1. Ingestion & Preprocessing:</strong> Parses raw text, datasheets, PDFs, images, and web URLs.
          </div>
          <div>
            <strong>2. Discovery Agent:</strong> Identifies manufacturer part numbers (MPN), brand, manufacturer, and catalog taxonomies.
          </div>
          <div>
            <strong>3. Knowledge Retrieval:</strong> Queries indexed permanent baseline knowledge corpus for matching datasheets.
          </div>
          <div>
            <strong>4. Knowledge Decision Engine:</strong> Analyzes evidence sufficiency and adaptively requests targeted research if gaps exist.
          </div>
          <div>
            <strong>5. Targeted Research:</strong> Executes focused acquisition to retrieve missing technical specifications.
          </div>
          <div>
            <strong>6. Intelligence Agent:</strong> Deep multi-agent LLM analysis extracting attributes, features, descriptions, and applications.
          </div>
          <div>
            <strong>7. Normalization Engine:</strong> Canonicalizes units of measure (UOM), decimal fractions, and standard nomenclature.
          </div>
          <div>
            <strong>8. Validation Engine:</strong> Executes deterministic rules, checks unit consistency, and flags conflicting evidence.
          </div>
          <div>
            <strong>9. Confidence Engine:</strong> Computes empirical field-level and overall qualitative confidence (HIGH, MEDIUM, LOW, CONFLICT).
          </div>
          <div>
            <strong>10. Commerce Output Adapter:</strong> Formats verified specifications into the authoritative 252-column commerce schema.
          </div>
        </div>
      </div>

      {/* Confidence Indicators Guide */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={18} color="#059669" />
            <h2 className="card-title">Qualitative Confidence Indicator Standards</h2>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '0.825rem' }}>
          <div style={{ padding: '12px', borderRadius: '6px', backgroundColor: '#ecfdf5', border: '1px solid #a7f3d0' }}>
            <div style={{ fontWeight: 700, color: '#065f46', marginBottom: '4px' }}>HIGH CONFIDENCE</div>
            <div style={{ color: '#047857' }}>
              Directly supported by authoritative manufacturer documentation or official catalog specs. Complete evidence provenance verified.
            </div>
          </div>

          <div style={{ padding: '12px', borderRadius: '6px', backgroundColor: '#fffbeb', border: '1px solid #fde68a' }}>
            <div style={{ fontWeight: 700, color: '#92400e', marginBottom: '4px' }}>MEDIUM CONFIDENCE</div>
            <div style={{ color: '#b45309' }}>
              Extracted from secondary distributor datasheets or inferred via standard category rules with high probability.
            </div>
          </div>

          <div style={{ padding: '12px', borderRadius: '6px', backgroundColor: '#fff7ed', border: '1px solid #fed7aa' }}>
            <div style={{ fontWeight: 700, color: '#9a3412', marginBottom: '4px' }}>LOW CONFIDENCE</div>
            <div style={{ color: '#c2410c' }}>
              Sparse evidence available; specifications derived from partial catalog matches. Manual review recommended.
            </div>
          </div>

          <div style={{ padding: '12px', borderRadius: '6px', backgroundColor: '#fef2f2', border: '1px solid #fecaca' }}>
            <div style={{ fontWeight: 700, color: '#991b1b', marginBottom: '4px' }}>CONFLICT / DISCREPANCY</div>
            <div style={{ color: '#b91c1c' }}>
              Multiple sources provide contradictory values for the same specification. Flagged in Validation Center for resolution.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
