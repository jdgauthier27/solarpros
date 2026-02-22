import React, { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  getDashboardOverview,
  getDashboardFunnel,
  getScoreDistribution,
  type DashboardOverview,
  type FunnelStage,
  type ScoreDistribution,
} from "../../api/client";

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const containerStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 24,
};

const headerStyle: React.CSSProperties = {
  fontSize: 24,
  fontWeight: 700,
  color: "#1a1a2e",
  marginBottom: 4,
};

const kpiRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))",
  gap: 16,
};

const kpiCardStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 10,
  padding: "18px 20px",
  boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
  display: "flex",
  flexDirection: "column",
  gap: 4,
};

const kpiLabelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#888",
  textTransform: "uppercase",
  letterSpacing: 0.5,
};

const kpiValueStyle: React.CSSProperties = {
  fontSize: 26,
  fontWeight: 700,
  color: "#1a1a2e",
};

const chartRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: 24,
};

const chartCardStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 10,
  padding: 24,
  boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
};

const chartTitleStyle: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 600,
  color: "#1a1a2e",
  marginBottom: 16,
};

const FUNNEL_COLORS = ["#4fc3f7", "#29b6f6", "#0288d1", "#01579b", "#002f6c"];
const DIST_COLOR = "#f9a825";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function Dashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [funnel, setFunnel] = useState<FunnelStage[]>([]);
  const [distribution, setDistribution] = useState<ScoreDistribution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        setLoading(true);
        const [overviewData, funnelData, distData] = await Promise.all([
          getDashboardOverview(),
          getDashboardFunnel(),
          getScoreDistribution(),
        ]);
        if (!cancelled) {
          setOverview(overviewData);
          setFunnel(funnelData);
          setDistribution(distData);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "#888" }}>
        Loading dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "#d32f2f" }}>
        Error: {error}
      </div>
    );
  }

  if (!overview) return null;

  const kpis: { label: string; value: string | number }[] = [
    { label: "Total Properties", value: overview.total_properties },
    { label: "Analyzed", value: overview.total_analyzed },
    { label: "Scored", value: overview.total_scored },
    { label: "Tier A", value: overview.tier_a_count },
    { label: "Tier B", value: overview.tier_b_count },
    { label: "Tier C", value: overview.tier_c_count },
    { label: "Avg Score", value: overview.avg_score.toFixed(1) },
    { label: "Emails Sent", value: overview.total_emails_sent },
    { label: "Opens", value: overview.total_opens },
    { label: "Replies", value: overview.total_replies },
  ];

  return (
    <div style={containerStyle}>
      <h1 style={headerStyle}>Dashboard</h1>

      {/* KPI Cards */}
      <div style={kpiRowStyle}>
        {kpis.map((kpi) => (
          <div key={kpi.label} style={kpiCardStyle}>
            <span style={kpiLabelStyle}>{kpi.label}</span>
            <span style={kpiValueStyle}>{kpi.value}</span>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div style={chartRowStyle}>
        {/* Pipeline Funnel */}
        <div style={chartCardStyle}>
          <div style={chartTitleStyle}>Pipeline Funnel</div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={funnel}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="stage" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {funnel.map((_entry, index) => (
                  <Cell
                    key={`funnel-${index}`}
                    fill={FUNNEL_COLORS[index % FUNNEL_COLORS.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Score Distribution */}
        <div style={chartCardStyle}>
          <div style={chartTitleStyle}>Score Distribution</div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={distribution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="bucket" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill={DIST_COLOR} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
