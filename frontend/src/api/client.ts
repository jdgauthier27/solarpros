import axios from "axios";

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api/v1",
  headers: { "Content-Type": "application/json" },
});

export { api };
export default api;

// ---------------------------------------------------------------------------
// TypeScript interfaces
// ---------------------------------------------------------------------------

export interface Property {
  id: string;
  apn: string;
  address: string;
  city: string;
  county: string;
  state: string;
  zip_code: string;
  latitude: number;
  longitude: number;
  year_built: number | null;
  square_footage: number | null;
  roof_area_sqft: number | null;
  stories: number | null;
  owner_name: string | null;
  owner_email: string | null;
  owner_phone: string | null;
  mailing_address: string | null;
}

export interface PropertyDetail extends Property {
  solar_analysis: SolarAnalysis | null;
  score: ScoreResult | null;
  email_outreach: EmailOutreach | null;
}

export interface SolarAnalysis {
  id: string;
  property_id: string;
  system_size_kw: number;
  annual_production_kwh: number;
  annual_savings_usd: number;
  installation_cost_usd: number;
  payback_years: number;
  co2_offset_tons: number;
  roof_utilization_pct: number;
  sun_hours_per_day: number;
}

export interface ScoreResult {
  id: string;
  property_id: string;
  total_score: number;
  tier: "A" | "B" | "C";
  solar_score: number;
  financial_score: number;
  property_score: number;
  owner_score: number;
}

export interface EmailOutreach {
  id: string;
  property_id: string;
  campaign_id: string;
  status: string;
  sent_at: string | null;
  opened_at: string | null;
  clicked_at: string | null;
  replied_at: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface PropertyFilters {
  county?: string;
  tier?: string;
  min_score?: number;
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}

export interface GeoJSONFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number];
  };
  properties: {
    id: string;
    apn: string;
    address: string;
    county: string;
    is_commercial: boolean;
    roof_sqft: number | null;
    tier: string | null;
    score: number | null;
    owner_name: string | null;
    system_size_kw: number | null;
  };
}

export interface GeoJSONCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
}

export interface ScoreDistribution {
  bucket: string;
  count: number;
}

export interface Campaign {
  id: string;
  name: string;
  status: "draft" | "active" | "paused" | "completed";
  tier_filter: string | null;
  min_score: number | null;
  total_recipients: number;
  created_at: string;
  updated_at: string;
  sequences: unknown[];
}

export interface CampaignCreate {
  name: string;
  tier_filter?: string;
  min_score?: number;
}

export interface CampaignMetrics {
  campaign_id: string;
  total_sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
  bounced: number;
  delivery_rate: number;
  open_rate: number;
  click_rate: number;
  reply_rate: number;
}

export interface PipelineStatus {
  pipeline_id: string;
  status: "pending" | "running" | "completed" | "failed" | "no_runs";
  current_stage: string | null;
  progress_pct: number;
  started_at: string;
  completed_at: string | null;
  error: string | null;
  runs: AgentRun[];
  progress: Record<string, string>;
}

export interface AgentRun {
  id: string;
  pipeline_id: string;
  agent_type: string;
  status: "pending" | "running" | "completed" | "failed";
  items_processed: number;
  items_failed: number;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  error_message: string | null;
}

export interface DashboardOverview {
  total_properties: number;
  total_analyzed: number;
  total_scored: number;
  total_campaigns: number;
  tier_a_count: number;
  tier_b_count: number;
  tier_c_count: number;
  avg_score: number;
  total_emails_sent: number;
  total_opens: number;
  total_replies: number;
}

export interface FunnelStage {
  stage: string;
  count: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getProperties(
  filters: PropertyFilters = {}
): Promise<PaginatedResponse<Property>> {
  const { data } = await api.get("/properties/", { params: filters });
  return data;
}

export async function getPropertyDetail(id: string): Promise<PropertyDetail> {
  const { data } = await api.get(`/properties/${id}`);
  return data;
}

export async function getPropertyMap(
  county?: string
): Promise<GeoJSONCollection> {
  const { data } = await api.get("/properties/map", {
    params: county ? { county } : {},
  });
  return data;
}

export async function getPropertyStats(): Promise<Record<string, unknown>> {
  const { data } = await api.get("/properties/stats");
  return data;
}

export async function getScores(
  params: Record<string, string | number> = {}
): Promise<any[]> {
  const { data } = await api.get("/scores/", { params });
  return Array.isArray(data) ? data : data.items ?? data;
}

export async function getScoreDistribution(): Promise<ScoreDistribution[]> {
  const { data } = await api.get("/scores/distribution");
  return data;
}

export async function getCampaigns(): Promise<Campaign[]> {
  const { data } = await api.get("/campaigns/");
  return data;
}

export async function createCampaign(
  payload: CampaignCreate
): Promise<Campaign> {
  const { data } = await api.post("/campaigns/", payload);
  return data;
}

export async function getCampaignMetrics(
  campaignId: string
): Promise<CampaignMetrics> {
  const { data } = await api.get(`/campaigns/${campaignId}/metrics`);
  return data;
}

export async function pauseCampaign(campaignId: string): Promise<Campaign> {
  const { data } = await api.post(`/campaigns/${campaignId}/pause`);
  return data;
}

export async function resumeCampaign(campaignId: string): Promise<Campaign> {
  const { data } = await api.post(`/campaigns/${campaignId}/resume`);
  return data;
}

export async function startPipeline(payload: {
  counties: string[];
  use_mock: boolean;
}): Promise<PipelineStatus> {
  const { data } = await api.post("/agents/pipeline/start", payload);
  return data;
}

export async function getPipelineStatus(): Promise<PipelineStatus> {
  const { data } = await api.get("/agents/pipeline/status");
  return data;
}

export async function getAgentRuns(): Promise<AgentRun[]> {
  const { data } = await api.get("/agents/runs");
  return data;
}

export async function getDashboardOverview(): Promise<DashboardOverview> {
  const { data } = await api.get("/dashboard/overview");
  return data;
}

export async function getDashboardFunnel(): Promise<FunnelStage[]> {
  const { data } = await api.get("/dashboard/funnel");
  return data;
}
