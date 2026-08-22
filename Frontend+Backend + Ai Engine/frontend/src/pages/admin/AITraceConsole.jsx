import React, { useState, useEffect, useRef } from 'react';
import { Activity, X, Loader2, ListTree } from 'lucide-react';

export default function AITraceConsole() {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const eventSourceRef = useRef(null);
  const sequenceRef = useRef(0);

  useEffect(() => {
    // 1. Fetch recent events to hydrate
    const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';
    fetch(`${API_BASE_URL}/traces/recent?limit=50`)
      .then(res => res.json())
      .then(data => {
        if (data && data.length > 0) {
          setEvents(data);
          // Get the highest sequence number
          const maxSeq = Math.max(...data.map(e => e.sequence));
          sequenceRef.current = maxSeq;
        }
        connectSSE();
      })
      .catch(err => {
        console.error("Failed to fetch recent traces", err);
        connectSSE();
      });

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const connectSSE = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    
    const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';
    let url = `${API_BASE_URL}/traces/stream`;
    if (sequenceRef.current > 0) {
      url += `?after_sequence=${sequenceRef.current}`;
    }

    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
    };

    es.onerror = (e) => {
      console.error('SSE error:', e);
      setConnected(false);
      es.close();
      // Reconnect after 3s
      setTimeout(connectSSE, 3000);
    };

    es.addEventListener('trace_event', (e) => {
      try {
        const eventData = JSON.parse(e.data);
        if (eventData.sequence > sequenceRef.current) {
          sequenceRef.current = eventData.sequence;
        }
        setEvents(prev => [eventData, ...prev].slice(0, 500)); // Keep last 500
      } catch (err) {
        console.error("Failed to parse event", err);
      }
    });
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'COMPLETED': return '#10b981'; // green-500
      case 'IN_PROGRESS': return '#3b82f6'; // blue-500
      case 'FAILED': return '#ef4444'; // red-500
      default: return '#64748b'; // slate-500
    }
  };

  return (
    <div style={{ padding: '24px', color: '#f8fafc', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.5rem', fontWeight: 'bold' }}>
          <ListTree size={24} /> Live AI Pipeline Trace
        </h1>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '8px', 
          padding: '6px 12px', 
          borderRadius: '999px',
          backgroundColor: connected ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
          color: connected ? '#10b981' : '#f59e0b',
          border: `1px solid ${connected ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)'}`,
          fontSize: '0.875rem'
        }}>
          {connected ? 'Connected (Live)' : 'Reconnecting...'}
          {connected && <Activity size={14} />}
          {!connected && <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />}
        </div>
      </div>

      <div style={{ 
        backgroundColor: '#1e293b', 
        borderRadius: '8px', 
        border: '1px solid #334155',
        overflow: 'hidden'
      }}>
        <div style={{ overflowX: 'auto', maxHeight: 'calc(100vh - 150px)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
            <thead style={{ backgroundColor: '#0f172a', position: 'sticky', top: 0, zIndex: 10 }}>
              <tr>
                <th style={{ padding: '12px 16px', borderBottom: '1px solid #334155', fontWeight: 600, color: '#94a3b8' }}>Time</th>
                <th style={{ padding: '12px 16px', borderBottom: '1px solid #334155', fontWeight: 600, color: '#94a3b8' }}>Job ID</th>
                <th style={{ padding: '12px 16px', borderBottom: '1px solid #334155', fontWeight: 600, color: '#94a3b8' }}>Stage</th>
                <th style={{ padding: '12px 16px', borderBottom: '1px solid #334155', fontWeight: 600, color: '#94a3b8' }}>Component</th>
                <th style={{ padding: '12px 16px', borderBottom: '1px solid #334155', fontWeight: 600, color: '#94a3b8' }}>Status</th>
                <th style={{ padding: '12px 16px', borderBottom: '1px solid #334155', fontWeight: 600, color: '#94a3b8' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {events.map((evt) => (
                <tr 
                  key={evt.event_id} 
                  onClick={() => setSelectedEvent(evt)}
                  style={{ 
                    cursor: 'pointer',
                    borderBottom: '1px solid #334155',
                    transition: 'background-color 0.15s',
                  }}
                  onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#334155'}
                  onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <td style={{ padding: '12px 16px', whiteSpace: 'nowrap' }}>{new Date(evt.timestamp).toLocaleTimeString()}</td>
                  <td style={{ padding: '12px 16px', fontFamily: 'monospace', color: '#cbd5e1' }}>
                    {evt.job_id?.substring(0,8) || evt.trace_id?.substring(0,8)}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ 
                      padding: '2px 8px', 
                      borderRadius: '4px', 
                      backgroundColor: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      fontSize: '0.75rem'
                    }}>
                      {evt.stage}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', color: '#cbd5e1' }}>{evt.component || '-'}</td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ 
                      padding: '2px 8px', 
                      borderRadius: '4px', 
                      backgroundColor: `${getStatusColor(evt.status)}20`,
                      color: getStatusColor(evt.status),
                      border: `1px solid ${getStatusColor(evt.status)}40`,
                      fontSize: '0.75rem',
                      fontWeight: 500
                    }}>
                      {evt.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <button 
                      onClick={(e) => { e.stopPropagation(); setSelectedEvent(evt); }}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#3b82f6',
                        cursor: 'pointer',
                        fontSize: '0.875rem'
                      }}
                    >
                      View Payload
                    </button>
                  </td>
                </tr>
              ))}
              {events.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                    No trace events found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedEvent && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 50,
          padding: '20px'
        }}>
          <div style={{
            backgroundColor: '#1e293b',
            borderRadius: '8px',
            width: '100%',
            maxWidth: '800px',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
          }}>
            <div style={{ 
              padding: '16px 24px', 
              borderBottom: '1px solid #334155',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Event Details ({selectedEvent.stage})</h2>
              <button 
                onClick={() => setSelectedEvent(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>
            
            <div style={{ padding: '24px', overflowY: 'auto' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>Event Type</div>
                  <div style={{ fontWeight: 500 }}>{selectedEvent.event_type}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>Status</div>
                  <div style={{ color: getStatusColor(selectedEvent.status), fontWeight: 500 }}>{selectedEvent.status}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>Trace ID</div>
                  <div style={{ fontFamily: 'monospace' }}>{selectedEvent.trace_id}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>Job ID</div>
                  <div style={{ fontFamily: 'monospace' }}>{selectedEvent.job_id}</div>
                </div>
              </div>
              
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem' }}>Payload</h3>
              <div style={{ 
                backgroundColor: '#0f172a', 
                padding: '16px', 
                borderRadius: '6px',
                border: '1px solid #334155',
                overflowX: 'auto'
              }}>
                <pre style={{ margin: 0, fontFamily: 'monospace', fontSize: '0.875rem', color: '#e2e8f0' }}>
                  {JSON.stringify(selectedEvent.payload, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
