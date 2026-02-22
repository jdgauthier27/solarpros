import React, { useEffect, useState, useCallback } from 'react';
import { getScores } from '../../api/client';

interface Prospect {
  id: string;
  property_id: string;
  address: string;
  city: string;
  county: string;
  building_type: string | null;
  roof_sqft: number | null;
  year_built: number | null;
  owner_name: string | null;
  entity_type: string | null;
  email: string | null;
  email_verified: boolean;
  system_size_kw: number | null;
  annual_savings: number | null;
  payback_years: number | null;
  composite_score: number;
  tier: string;
  solar_potential_score: number;
  roof_size_score: number;
  savings_score: number;
  utility_zone_score: number;
  owner_type_score: number;
  contact_quality_score: number;
  building_age_score: number;
}

const TIERS = ['All', 'A', 'B', 'C'];
const PAGE_SIZE = 25;

type SortField = 'composite_score' | 'annual_savings' | 'system_size_kw' | 'roof_sqft' | 'payback_years';

const ProspectTable: React.FC = () => {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tier, setTier] = useState('All');
  const [minScore, setMinScore] = useState(0);
  const [page, setPage] = useState(0);
  const [sortField, setSortField] = useState<SortField>('composite_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = { skip: page * PAGE_SIZE, limit: PAGE_SIZE };
      if (tier !== 'All') params.tier = tier;
      if (minScore > 0) params.min_score = minScore;
      const data = await getScores(params);
      setProspects(data);
    } catch (err) {
      setError('Failed to load prospects');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, tier, minScore]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const sorted = [...prospects].sort((a, b) => {
    const av = (a[sortField] as number) ?? 0;
    const bv = (b[sortField] as number) ?? 0;
    return sortDir === 'asc' ? av - bv : bv - av;
  });

  const sortIcon = (field: SortField) => sortField === field ? (sortDir === 'asc' ? ' \u25B2' : ' \u25BC') : '';

  const fmt = (n: number | null) => n != null ? n.toLocaleString() : '-';
  const fmtDollar = (n: number | null) => n != null ? `$${n.toLocaleString()}` : '-';

  return (
    <div style={{ padding: '24px', fontFamily: 'system-ui, sans-serif' }}>
      <h2 style={{ margin: '0 0 20px', fontSize: '24px', color: '#111827' }}>Scored Prospects</h2>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase' }}>Tier</span>
          <select style={selectStyle} value={tier} onChange={e => { setTier(e.target.value); setPage(0); }}>
            {TIERS.map(t => <option key={t} value={t}>{t === 'All' ? 'All Tiers' : `Tier ${t}`}</option>)}
          </select>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase' }}>Min Score</span>
          <input type="number" style={{ ...selectStyle, width: '80px' }} value={minScore} min={0} max={100}
            onChange={e => { setMinScore(Number(e.target.value)); setPage(0); }} />
        </div>
        <span style={{ fontSize: '13px', color: '#9ca3af', marginLeft: 'auto' }}>
          {!loading && `Showing ${sorted.length} prospects (page ${page + 1})`}
        </span>
      </div>

      {error && <div style={{ color: '#dc2626', padding: '12px', background: '#fef2f2', borderRadius: '8px', marginBottom: '16px' }}>{error}</div>}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: '#6b7280' }}>Loading prospects...</div>
      ) : (
        <>
          <div style={{ background: '#fff', borderRadius: '12px', border: '1px solid #e5e7eb', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  <th style={thStyle}>Address</th>
                  <th style={thStyle}>County</th>
                  <th style={thStyle}>Owner</th>
                  <th style={thStyle}>Tier</th>
                  <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => handleSort('composite_score')}>Score{sortIcon('composite_score')}</th>
                  <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => handleSort('system_size_kw')}>System{sortIcon('system_size_kw')}</th>
                  <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => handleSort('annual_savings')}>Savings/yr{sortIcon('annual_savings')}</th>
                  <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => handleSort('payback_years')}>Payback{sortIcon('payback_years')}</th>
                  <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => handleSort('roof_sqft')}>Roof sqft{sortIcon('roof_sqft')}</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map(p => (
                  <React.Fragment key={p.id}>
                    <tr
                      style={{ cursor: 'pointer', transition: 'background 0.1s' }}
                      onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}
                      onMouseEnter={e => (e.currentTarget.style.backgroundColor = '#f9fafb')}
                      onMouseLeave={e => (e.currentTarget.style.backgroundColor = '')}
                    >
                      <td style={tdStyle}>
                        <div style={{ fontWeight: 500, color: '#111827' }}>{p.address}</div>
                        <div style={{ fontSize: '11px', color: '#9ca3af' }}>{p.city}</div>
                      </td>
                      <td style={tdStyle}>{p.county}</td>
                      <td style={tdStyle}>
                        <div style={{ fontWeight: 500, color: '#111827' }}>{p.owner_name || '-'}</div>
                        <div style={{ fontSize: '11px', color: '#9ca3af' }}>{p.entity_type || ''}</div>
                      </td>
                      <td style={tdStyle}><span style={tierBadge(p.tier)}>{p.tier}</span></td>
                      <td style={{ ...tdStyle, fontWeight: 700, color: '#111827' }}>{p.composite_score}</td>
                      <td style={tdStyle}>{p.system_size_kw ? `${p.system_size_kw} kW` : '-'}</td>
                      <td style={{ ...tdStyle, color: '#059669', fontWeight: 500 }}>{fmtDollar(p.annual_savings)}</td>
                      <td style={tdStyle}>{p.payback_years ? `${p.payback_years} yr` : '-'}</td>
                      <td style={tdStyle}>{fmt(p.roof_sqft)}</td>
                    </tr>
                    {expandedId === p.id && (
                      <tr>
                        <td colSpan={9} style={{ padding: '16px 20px', background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
                            <div>
                              <div style={detailLabel}>Building</div>
                              <div style={detailValue}>{p.building_type || '-'} | {p.year_built || '-'}</div>
                            </div>
                            <div>
                              <div style={detailLabel}>Email</div>
                              <div style={detailValue}>
                                {p.email || 'N/A'}
                                {p.email_verified && <span style={{ color: '#059669', marginLeft: '4px' }}> verified</span>}
                              </div>
                            </div>
                            <div>
                              <div style={detailLabel}>Score Breakdown</div>
                              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                {([
                                  ['Solar', p.solar_potential_score],
                                  ['Roof', p.roof_size_score],
                                  ['Savings', p.savings_score],
                                  ['Utility', p.utility_zone_score],
                                  ['Owner', p.owner_type_score],
                                  ['Contact', p.contact_quality_score],
                                  ['Age', p.building_age_score],
                                ] as [string, number][]).map(([label, val]) => (
                                  <span key={label} style={{ fontSize: '11px', padding: '2px 6px', background: scoreColor(val), borderRadius: '4px', color: '#fff' }}>
                                    {label}: {val}
                                  </span>
                                ))}
                              </div>
                            </div>
                            <div>
                              <div style={detailLabel}>Property ID</div>
                              <div style={{ ...detailValue, fontSize: '11px', fontFamily: 'monospace' }}>{p.property_id}</div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
                {sorted.length === 0 && (
                  <tr><td colSpan={9} style={{ ...tdStyle, textAlign: 'center', color: '#9ca3af', padding: '40px' }}>No prospects found</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', gap: '8px', marginTop: '16px', alignItems: 'center', justifyContent: 'center' }}>
            <button style={pageBtn(page === 0)} disabled={page === 0} onClick={() => setPage(p => p - 1)}>Previous</button>
            <span style={{ color: '#6b7280', fontSize: '14px' }}>Page {page + 1}</span>
            <button style={pageBtn(sorted.length < PAGE_SIZE)} disabled={sorted.length < PAGE_SIZE} onClick={() => setPage(p => p + 1)}>Next</button>
          </div>
        </>
      )}
    </div>
  );
};

// Styles
const selectStyle: React.CSSProperties = { padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '14px', background: '#fff' };
const thStyle: React.CSSProperties = { padding: '10px 16px', textAlign: 'left', borderBottom: '2px solid #e5e7eb', fontWeight: 600, color: '#374151', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px', userSelect: 'none' };
const tdStyle: React.CSSProperties = { padding: '10px 16px', borderBottom: '1px solid #f3f4f6', color: '#4b5563', verticalAlign: 'top' };
const detailLabel: React.CSSProperties = { fontSize: '11px', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', marginBottom: '4px' };
const detailValue: React.CSSProperties = { fontSize: '13px', color: '#111827' };

const tierBadge = (tier: string): React.CSSProperties => ({
  display: 'inline-block', padding: '2px 10px', borderRadius: '12px', fontWeight: 600, fontSize: '12px',
  backgroundColor: tier === 'A' ? '#dcfce7' : tier === 'B' ? '#fef3c7' : '#fee2e2',
  color: tier === 'A' ? '#166534' : tier === 'B' ? '#92400e' : '#991b1b',
});

const scoreColor = (val: number): string => {
  if (val >= 80) return '#059669';
  if (val >= 60) return '#d97706';
  if (val >= 40) return '#ea580c';
  return '#dc2626';
};

const pageBtn = (disabled: boolean): React.CSSProperties => ({
  padding: '8px 16px', border: '1px solid #d1d5db', borderRadius: '6px', cursor: disabled ? 'not-allowed' : 'pointer',
  backgroundColor: disabled ? '#f9fafb' : '#fff', color: disabled ? '#9ca3af' : '#374151', fontSize: '14px',
});

export default ProspectTable;
