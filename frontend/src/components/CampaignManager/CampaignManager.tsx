import React, { useEffect, useState } from 'react';
import { getCampaigns, createCampaign, getCampaignMetrics, api } from '../../api/client';

interface Campaign {
  id: string;
  name: string;
  status: string;
  tier_filter: string | null;
  min_score: number | null;
  created_at: string;
  sequences: unknown[];
}

interface Metrics {
  total_sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
  bounced: number;
  open_rate: number;
  click_rate: number;
  reply_rate: number;
}

const statusColors: Record<string, { bg: string; text: string }> = {
  active: { bg: '#dcfce7', text: '#166534' },
  paused: { bg: '#fef3c7', text: '#92400e' },
  draft: { bg: '#f3f4f6', text: '#6b7280' },
  completed: { bg: '#dbeafe', text: '#1e40af' },
};

const styles = {
  container: { padding: '24px', fontFamily: 'system-ui, sans-serif' } as React.CSSProperties,
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' } as React.CSSProperties,
  card: { background: '#fff', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '20px' } as React.CSSProperties,
  form: { display: 'flex', flexDirection: 'column' as const, gap: '12px' } as React.CSSProperties,
  input: { padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '14px' } as React.CSSProperties,
  button: { padding: '10px 20px', backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '14px', cursor: 'pointer', fontWeight: 600 } as React.CSSProperties,
  campaignItem: (selected: boolean) => ({
    padding: '12px 16px', borderRadius: '8px', cursor: 'pointer', marginBottom: '8px',
    border: selected ? '2px solid #2563eb' : '1px solid #e5e7eb',
    backgroundColor: selected ? '#eff6ff' : '#fff',
  }) as React.CSSProperties,
  badge: (status: string) => ({
    display: 'inline-block', padding: '2px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 600,
    backgroundColor: statusColors[status]?.bg ?? '#f3f4f6',
    color: statusColors[status]?.text ?? '#6b7280',
  }) as React.CSSProperties,
  metricCard: { textAlign: 'center' as const, padding: '12px' } as React.CSSProperties,
  metricValue: { fontSize: '24px', fontWeight: 700, color: '#111827' } as React.CSSProperties,
  metricLabel: { fontSize: '12px', color: '#6b7280', marginTop: '4px' } as React.CSSProperties,
};

const CampaignManager: React.FC = () => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [formName, setFormName] = useState('');
  const [formTier, setFormTier] = useState('A,B');
  const [formMinScore, setFormMinScore] = useState(50);

  const fetchCampaigns = async () => {
    try {
      const data = await getCampaigns();
      setCampaigns(data);
    } catch (err) {
      console.error('Failed to load campaigns', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCampaigns(); }, []);

  useEffect(() => {
    if (!selectedId) { setMetrics(null); return; }
    getCampaignMetrics(selectedId).then(setMetrics).catch(console.error);
  }, [selectedId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) return;
    try {
      await createCampaign({ name: formName, tier_filter: formTier, min_score: formMinScore });
      setFormName('');
      fetchCampaigns();
    } catch (err) {
      console.error('Failed to create campaign', err);
    }
  };

  const handleTogglePause = async (campaign: Campaign) => {
    const newStatus = campaign.status === 'active' ? 'paused' : 'active';
    try {
      await api.patch(`/campaigns/${campaign.id}`, { status: newStatus });
      fetchCampaigns();
    } catch (err) {
      console.error('Failed to update campaign', err);
    }
  };

  const selected = campaigns.find(c => c.id === selectedId);

  return (
    <div style={styles.container}>
      <h2 style={{ margin: '0 0 20px', fontSize: '24px', color: '#111827' }}>Campaign Manager</h2>

      <div style={styles.grid}>
        <div>
          <div style={{ ...styles.card, marginBottom: '16px' }}>
            <h3 style={{ margin: '0 0 12px', fontSize: '16px' }}>Create Campaign</h3>
            <form style={styles.form} onSubmit={handleCreate}>
              <input style={styles.input} placeholder="Campaign name" value={formName} onChange={e => setFormName(e.target.value)} />
              <select style={styles.input} value={formTier} onChange={e => setFormTier(e.target.value)}>
                <option value="A">Tier A only</option>
                <option value="A,B">Tier A & B</option>
                <option value="A,B,C">All tiers</option>
              </select>
              <input style={styles.input} type="number" placeholder="Min score" value={formMinScore} onChange={e => setFormMinScore(Number(e.target.value))} />
              <button style={styles.button} type="submit">Create Campaign</button>
            </form>
          </div>

          <div style={styles.card}>
            <h3 style={{ margin: '0 0 12px', fontSize: '16px' }}>Campaigns</h3>
            {loading ? <p style={{ color: '#6b7280' }}>Loading...</p> : campaigns.length === 0 ? <p style={{ color: '#9ca3af' }}>No campaigns yet</p> : (
              campaigns.map(c => (
                <div key={c.id} style={styles.campaignItem(c.id === selectedId)} onClick={() => setSelectedId(c.id)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong>{c.name}</strong>
                    <span style={styles.badge(c.status)}>{c.status}</span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
                    Tier: {c.tier_filter ?? 'All'} | Min: {c.min_score ?? 0} | {new Date(c.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div style={styles.card}>
          {selected ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '18px' }}>{selected.name}</h3>
                {(selected.status === 'active' || selected.status === 'paused') && (
                  <button style={{ ...styles.button, backgroundColor: selected.status === 'active' ? '#f59e0b' : '#22c55e' }} onClick={() => handleTogglePause(selected)}>
                    {selected.status === 'active' ? 'Pause' : 'Resume'}
                  </button>
                )}
              </div>

              {metrics ? (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '20px' }}>
                    {[
                      { label: 'Sent', value: metrics.total_sent },
                      { label: 'Delivered', value: metrics.delivered },
                      { label: 'Opened', value: metrics.opened },
                      { label: 'Clicked', value: metrics.clicked },
                      { label: 'Replied', value: metrics.replied },
                      { label: 'Bounced', value: metrics.bounced },
                    ].map(m => (
                      <div key={m.label} style={styles.metricCard}>
                        <div style={styles.metricValue}>{m.value}</div>
                        <div style={styles.metricLabel}>{m.label}</div>
                      </div>
                    ))}
                  </div>
                  <h4 style={{ margin: '0 0 8px', fontSize: '14px', color: '#374151' }}>Rates</h4>
                  <div style={{ display: 'flex', gap: '24px' }}>
                    <div><strong>{(metrics.open_rate * 100).toFixed(1)}%</strong> <span style={{ color: '#6b7280', fontSize: '12px' }}>Open</span></div>
                    <div><strong>{(metrics.click_rate * 100).toFixed(1)}%</strong> <span style={{ color: '#6b7280', fontSize: '12px' }}>Click</span></div>
                    <div><strong>{(metrics.reply_rate * 100).toFixed(1)}%</strong> <span style={{ color: '#6b7280', fontSize: '12px' }}>Reply</span></div>
                  </div>
                </>
              ) : <p style={{ color: '#6b7280' }}>Loading metrics...</p>}
            </>
          ) : (
            <p style={{ color: '#9ca3af', textAlign: 'center', paddingTop: '40px' }}>Select a campaign to view details</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default CampaignManager;
