import React, { useEffect, useState, useRef } from 'react';
import { startPipeline, getPipelineStatus, getAgentRuns } from '../../api/client';

interface AgentRun {
  id: string;
  agent_type: string;
  status: string;
  items_processed: number;
  items_failed: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

interface PipelineStatus {
  status: string;
  runs: AgentRun[];
  progress: Record<string, string>;
}

const COUNTIES = ['Los Angeles', 'Orange', 'San Diego', 'Riverside', 'San Bernardino'];

const statusColors: Record<string, { bg: string; text: string }> = {
  running: { bg: '#dbeafe', text: '#1e40af' },
  completed: { bg: '#dcfce7', text: '#166534' },
  failed: { bg: '#fee2e2', text: '#991b1b' },
  pending: { bg: '#f3f4f6', text: '#6b7280' },
};

const styles = {
  container: { padding: '24px', fontFamily: 'system-ui, sans-serif' } as React.CSSProperties,
  card: { background: '#fff', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '20px', marginBottom: '20px' } as React.CSSProperties,
  checkboxGroup: { display: 'flex', gap: '16px', flexWrap: 'wrap' as const, marginBottom: '16px' } as React.CSSProperties,
  checkbox: { display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' } as React.CSSProperties,
  button: (disabled: boolean) => ({
    padding: '12px 24px', backgroundColor: disabled ? '#9ca3af' : '#2563eb', color: '#fff', border: 'none',
    borderRadius: '8px', fontSize: '16px', fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer',
  }) as React.CSSProperties,
  badge: (status: string) => ({
    display: 'inline-block', padding: '2px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 600,
    backgroundColor: statusColors[status]?.bg ?? '#f3f4f6',
    color: statusColors[status]?.text ?? '#6b7280',
  }) as React.CSSProperties,
  table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: '14px' } as React.CSSProperties,
  th: { padding: '10px 12px', textAlign: 'left' as const, borderBottom: '2px solid #e5e7eb', fontWeight: 600, color: '#374151' } as React.CSSProperties,
  td: { padding: '8px 12px', borderBottom: '1px solid #f3f4f6', color: '#4b5563' } as React.CSSProperties,
  pipelineStatus: { display: 'flex', gap: '16px', alignItems: 'center', padding: '16px', background: '#f9fafb', borderRadius: '8px', marginBottom: '16px' } as React.CSSProperties,
};

const AgentStatus: React.FC = () => {
  const [selectedCounties, setSelectedCounties] = useState<string[]>([...COUNTIES]);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [starting, setStarting] = useState(false);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<number | null>(null);

  const fetchStatus = async () => {
    try {
      const [status, allRuns] = await Promise.all([getPipelineStatus(), getAgentRuns()]);
      setPipelineStatus(status);
      setRuns(allRuns);
    } catch (err) {
      console.error('Failed to fetch status', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStatus(); }, []);

  // Auto-refresh when pipeline is running
  useEffect(() => {
    if (pipelineStatus?.status === 'running') {
      intervalRef.current = window.setInterval(fetchStatus, 5000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [pipelineStatus?.status]);

  const toggleCounty = (county: string) => {
    setSelectedCounties(prev =>
      prev.includes(county) ? prev.filter(c => c !== county) : [...prev, county]
    );
  };

  const handleStart = async () => {
    if (selectedCounties.length === 0) return;
    setStarting(true);
    try {
      await startPipeline({ counties: selectedCounties, use_mock: true });
      await fetchStatus();
    } catch (err) {
      console.error('Failed to start pipeline', err);
    } finally {
      setStarting(false);
    }
  };

  const formatTime = (ts: string | null) => {
    if (!ts) return '-';
    return new Date(ts).toLocaleString();
  };

  const isRunning = pipelineStatus?.status === 'running';

  return (
    <div style={styles.container}>
      <h2 style={{ margin: '0 0 20px', fontSize: '24px', color: '#111827' }}>Agent Status</h2>

      {/* Pipeline Control */}
      <div style={styles.card}>
        <h3 style={{ margin: '0 0 12px', fontSize: '16px' }}>Pipeline Control</h3>
        <div style={styles.checkboxGroup}>
          {COUNTIES.map(county => (
            <label key={county} style={styles.checkbox}>
              <input type="checkbox" checked={selectedCounties.includes(county)} onChange={() => toggleCounty(county)} />
              {county}
            </label>
          ))}
        </div>
        <button style={styles.button(starting || isRunning)} disabled={starting || isRunning || selectedCounties.length === 0} onClick={handleStart}>
          {starting ? 'Starting...' : isRunning ? 'Pipeline Running...' : 'Start Pipeline'}
        </button>
      </div>

      {/* Pipeline Status */}
      {pipelineStatus && pipelineStatus.status !== 'no_runs' && (
        <div style={styles.card}>
          <h3 style={{ margin: '0 0 12px', fontSize: '16px' }}>Current Pipeline</h3>
          <div style={styles.pipelineStatus}>
            <span style={styles.badge(pipelineStatus.status)}>{pipelineStatus.status}</span>
            {isRunning && <span style={{ color: '#6b7280', fontSize: '14px' }}>Auto-refreshing every 5s</span>}
          </div>
          {Object.keys(pipelineStatus.progress).length > 0 && (
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              {Object.entries(pipelineStatus.progress).map(([agent, status]) => (
                <div key={agent} style={{ padding: '8px 12px', background: '#f9fafb', borderRadius: '6px', fontSize: '13px' }}>
                  <strong>{agent.replace('_', ' ')}</strong>: <span style={styles.badge(status)}>{status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Run History */}
      <div style={styles.card}>
        <h3 style={{ margin: '0 0 12px', fontSize: '16px' }}>Run History</h3>
        {loading ? <p style={{ color: '#6b7280' }}>Loading...</p> : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Agent</th>
                <th style={styles.th}>Status</th>
                <th style={styles.th}>Processed</th>
                <th style={styles.th}>Failed</th>
                <th style={styles.th}>Started</th>
                <th style={styles.th}>Completed</th>
                <th style={styles.th}>Error</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(run => (
                <tr key={run.id}>
                  <td style={styles.td}>{run.agent_type.replace('_', ' ')}</td>
                  <td style={styles.td}><span style={styles.badge(run.status)}>{run.status}</span></td>
                  <td style={styles.td}>{run.items_processed}</td>
                  <td style={styles.td}>{run.items_failed}</td>
                  <td style={styles.td}>{formatTime(run.started_at)}</td>
                  <td style={styles.td}>{formatTime(run.completed_at)}</td>
                  <td style={{ ...styles.td, maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {run.error_message ?? '-'}
                  </td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr><td colSpan={7} style={{ ...styles.td, textAlign: 'center', color: '#9ca3af' }}>No runs yet</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default AgentStatus;
