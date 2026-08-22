import React, { useState } from 'react';
import { Settings as SettingsIcon, ShieldCheck, Database, HardDrive, Cpu, CheckCircle2 } from 'lucide-react';

export const Settings: React.FC = () => {
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="page-body" style={{ maxWidth: '800px' }}>
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f172a' }}>Platform Configuration & Settings</h1>
        <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '2px' }}>
          Manage AI providers, storage safety ceilings, and multi-agent orchestrator parameters
        </p>
      </div>

      {saved && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: '#ecfdf5',
            border: '1px solid #a7f3d0',
            borderRadius: '6px',
            color: '#065f46',
            fontSize: '0.85rem',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <CheckCircle2 size={16} />
          Configuration settings saved successfully.
        </div>
      )}

      {/* AI Engine Information Section */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={18} color="#2563eb" />
            <h2 className="card-title">AI Multi-Agent Engine</h2>
          </div>
        </div>

        <div style={{ marginBottom: '16px', fontSize: '0.85rem', color: '#334155' }}>
          <p>
            The backend engine operates in a decoupled, provider-agnostic manner. 
            All AI providers (Gemini, xAI, Ollama) and their credentials are securely 
            managed in the backend environment.
          </p>
          <p style={{ marginTop: '8px' }}>
            To change processing behavior, select the desired <strong>AI Mode</strong> (AUTO, FAST, DEEP, LOCAL) 
            during product upload. The backend will automatically orchestrate the correct local 
            and remote models.
          </p>
        </div>
      </div>

      {/* Storage Ceilings Section */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <HardDrive size={18} color="#059669" />
            <h2 className="card-title">Storage Safety & Retention Ceilings</h2>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', backgroundColor: '#f8fafc', borderRadius: '6px' }}>
            <div>
              <div style={{ fontSize: '0.825rem', fontWeight: 600, color: '#0f172a' }}>Permanent Knowledge Partition</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Controlled baseline industrial taxonomy</div>
            </div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#059669' }}>2 GiB Cap (Enforced)</div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', backgroundColor: '#f8fafc', borderRadius: '6px' }}>
            <div>
              <div style={{ fontSize: '0.825rem', fontWeight: 600, color: '#0f172a' }}>Temporary Cache Partition</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>LRU eviction with 7-day retention policy</div>
            </div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#059669' }}>2 GiB Cap (Enforced)</div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', backgroundColor: '#f8fafc', borderRadius: '6px' }}>
            <div>
              <div style={{ fontSize: '0.825rem', fontWeight: 600, color: '#0f172a' }}>Vector Storage Engine</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Inverted index with BM25 keyword matching</div>
            </div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#2563eb' }}>Active & Ready</div>
          </div>
        </div>
      </div>
    </div>
  );
};
