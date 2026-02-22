import React, { useEffect, useState, useCallback } from 'react';
import { getScores } from '../../api/client';

interface ProspectScore {
  id: string;
  property_id: string;
  owner_id: string | null;
  composite_score: number;
  tier: string;
  solar_potential_score: number;
  roof_size_score: number;
  savings_score: number;
  utility_zone_score: number;
  owner_type_score: number;
  contact_quality_score: number;
  building_age_score: number;
  scoring_version: number;
}

const COUNTIES = ['All', 'Los Angeles', 'Orange', 'San Diego', 'Riverside', 'San Bernardino'];
const TIERS = ['All', 'A', 'B', 'C'];
const PAGE_SIZE = 20;

const styles = {
  container: { padding: '24px', fontFamily: 'system-ui, sans-serif' } as React.CSSProperties,
  filters: { display: 'flex', gap: '16px', marginBottom: '20px', alignItems: 'center', flexWrap: 'wrap' as const } as React.CSSProperties,
  filterGroup: { display: 'flex', flexDirection: 'column' as const, gap: '4px' } as React.CSSProperties,
  label: { fontSize: '12px', fontWeight: 600, color: '#6b7280' } as React.CSSProperties,
  select: { padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '14px' } as React.CSSProperties,
  input: { padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '14px', width: '80px' } as React.CSSProperties,
  table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: '14px' } as React.CSSProperties,
  th: { padding: '12px 16px', textAlign: 'left' as const, borderBottom: '2px solid #e5e7eb', fontWeight: 600, color: '#374151', cursor: 'pointer', userSelect: 'none' as const } as React.CSSProperties,
  td: { padding: '10px 16px', borderBottom: '1px solid #f3f4f6', color: '#4b5563' } as React.CSSProperties,
  tierBadge: (tier: string) => ({
    display: 'inline-block', padding: '2px 10px', borderRadius: '12px', fontWeight: 600, fontSize: '12px',
    backgroundColor: tier === 'A' ? '#dcfce7' : tier === 'B' ? '#fef3c7' : '#fee2e2',
    color: tier === 'A' ? '#166534' : tier === 'B' ? '#92400e' : '#991b1b',
  }) as React.CSSProperties,
  pagination: { display: 'flex', gap: '8px', marginTop: '16px', alignItems: 'center', justifyContent: 'center' } as React.CSSProperties,
  pageBtn: (disabled: boolean) => ({
    padding: '8px 16px', border: '1px solid #d1d5db', borderRadius: '6px', cursor: disabled ? 'not-allowed' : 'pointer',
    backgroundColor: disabled ? '#f9fafb' : '#fff', color: disabled ? '#9ca3af' : '#374151',
  }) as React.CSSProperties,
};

type SortField = 'composite_score' | 'tier' | 'solar_potential_score' | 'roof_size_score' | 'savings_score';

const ProspectTable: React.FC = () => {
  const [scores, setScores] = useState<ProspectScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [county, setCounty] = useState('All');
  const [tier, setTier] = useState('All');
  const [minScore, setMinScore] = useState(0);
  const [page, setPage] = useState(0);
  const [sortField, setSortField] = useState<SortField>('composite_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const fetchScores = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
      if (tier !== 'All') params.tier = tier;
      if (minScore > 0) params.min_score = minScore;
      const data = await getScores(params);
      setScores(data);
    } catch (err) {
      console.error('Failed to fetch scores', err);
    } finally {
      setLoading(false);
    }
  }, [page, tier, minScore]);

  useEffect(() => { fetchScores(); }, [fetchScores]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const sorted = [...scores].sort((a, b) => {
    const av = a[sortField] ?? 0;
    const bv = b[sortField] ?? 0;
    return sortDir === 'asc' ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
  });

  const sortIcon = (field: SortField) => sortField === field ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';

  return (
    <div style={styles.container}>
      <h2 style={{ margin: '0 0 20px', fontSize: '24px', color: '#111827' }}>Scored Prospects</h2>

      <div style={styles.filters}>
        <div style={styles.filterGroup}>
          <span style={styles.label}>County</span>
          <select style={styles.select} value={county} onChange={e => { setCounty(e.target.value); setPage(0); }}>
            {COUNTIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div style={styles.filterGroup}>
          <span style={styles.label}>Tier</span>
          <select style={styles.select} value={tier} onChange={e => { setTier(e.target.value); setPage(0); }}>
            {TIERS.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div style={styles.filterGroup}>
          <span style={styles.label}>Min Score</span>
          <input type="number" style={styles.input} value={minScore} min={0} max={100}
            onChange={e => { setMinScore(Number(e.target.value)); setPage(0); }} />
        </div>
      </div>

      {loading ? (
        <p style={{ color: '#6b7280' }}>Loading prospects...</p>
      ) : (
        <>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Property ID</th>
                <th style={styles.th} onClick={() => handleSort('tier')}>Tier{sortIcon('tier')}</th>
                <th style={styles.th} onClick={() => handleSort('composite_score')}>Score{sortIcon('composite_score')}</th>
                <th style={styles.th} onClick={() => handleSort('solar_potential_score')}>Solar{sortIcon('solar_potential_score')}</th>
                <th style={styles.th} onClick={() => handleSort('roof_size_score')}>Roof{sortIcon('roof_size_score')}</th>
                <th style={styles.th} onClick={() => handleSort('savings_score')}>Savings{sortIcon('savings_score')}</th>
                <th style={styles.th}>Utility</th>
                <th style={styles.th}>Owner</th>
                <th style={styles.th}>Contact</th>
                <th style={styles.th}>Age</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(s => (
                <tr key={s.id} style={{ cursor: 'pointer' }} onMouseEnter={e => (e.currentTarget.style.backgroundColor = '#f9fafb')} onMouseLeave={e => (e.currentTarget.style.backgroundColor = '')}>
                  <td style={styles.td}>{s.property_id.slice(0, 8)}...</td>
                  <td style={styles.td}><span style={styles.tierBadge(s.tier)}>{s.tier}</span></td>
                  <td style={{ ...styles.td, fontWeight: 600 }}>{s.composite_score.toFixed(1)}</td>
                  <td style={styles.td}>{s.solar_potential_score.toFixed(0)}</td>
                  <td style={styles.td}>{s.roof_size_score.toFixed(0)}</td>
                  <td style={styles.td}>{s.savings_score.toFixed(0)}</td>
                  <td style={styles.td}>{s.utility_zone_score.toFixed(0)}</td>
                  <td style={styles.td}>{s.owner_type_score.toFixed(0)}</td>
                  <td style={styles.td}>{s.contact_quality_score.toFixed(0)}</td>
                  <td style={styles.td}>{s.building_age_score.toFixed(0)}</td>
                </tr>
              ))}
              {sorted.length === 0 && (
                <tr><td colSpan={10} style={{ ...styles.td, textAlign: 'center', color: '#9ca3af' }}>No prospects found</td></tr>
              )}
            </tbody>
          </table>

          <div style={styles.pagination}>
            <button style={styles.pageBtn(page === 0)} disabled={page === 0} onClick={() => setPage(p => p - 1)}>Previous</button>
            <span style={{ color: '#6b7280', fontSize: '14px' }}>Page {page + 1}</span>
            <button style={styles.pageBtn(sorted.length < PAGE_SIZE)} disabled={sorted.length < PAGE_SIZE} onClick={() => setPage(p => p + 1)}>Next</button>
          </div>
        </>
      )}
    </div>
  );
};

export default ProspectTable;
