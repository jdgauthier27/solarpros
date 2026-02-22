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
  // V2 metrics
  total_contacts: number;
  total_triggers: number;
  total_outreach_touches: number;
  channels_used: Record<string, number>;
}

export interface FunnelStage {
  stage: string;
  count: number;
}

// ---------------------------------------------------------------------------
// V2: Contact interfaces
// ---------------------------------------------------------------------------

export type BuyingRole =
  | "economic_buyer"
  | "champion"
  | "technical_evaluator"
  | "financial_evaluator"
  | "influencer";

export interface Contact {
  id: string;
  owner_id: string;
  full_name: string;
  first_name: string | null;
  last_name: string | null;
  job_title: string | null;
  buying_role: BuyingRole | null;
  email: string | null;
  email_verified: boolean;
  email_source: string | null;
  phone: string | null;
  phone_type: string | null;
  phone_source: string | null;
  linkedin_url: string | null;
  confidence_score: number;
  is_primary: boolean;
  opted_out: boolean;
  enrichment_sources: Record<string, boolean> | null;
  created_at: string | null;
}

// ---------------------------------------------------------------------------
// V2: Trigger event interfaces
// ---------------------------------------------------------------------------

export interface TriggerEvent {
  id: string;
  property_id: string;
  owner_id: string | null;
  event_type: string;
  title: string;
  source: string;
  source_url: string | null;
  detected_at: string;
  event_date: string | null;
  relevance_score: number;
  raw_data: Record<string, unknown> | null;
  created_at: string | null;
}

// ---------------------------------------------------------------------------
// V2: Outreach interfaces
// ---------------------------------------------------------------------------

export type OutreachChannel = "email" | "linkedin" | "phone" | "direct_mail";

export interface OutreachTouch {
  id: string;
  campaign_id: string;
  contact_id: string;
  channel: OutreachChannel;
  status: string;
  sendgrid_message_id: string | null;
  sent_at: string | null;
  opened_at: string | null;
  replied_at: string | null;
  call_duration_seconds: number | null;
  call_outcome: string | null;
  linkedin_connection_status: string | null;
  response_type: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface OutreachTouchUpdate {
  status?: string;
  call_duration_seconds?: number;
  call_outcome?: string;
  linkedin_connection_status?: string;
  response_type?: string;
  notes?: string;
}

// ---------------------------------------------------------------------------
// Takeoff interfaces
// ---------------------------------------------------------------------------

export interface TakeoffProject {
  id: string;
  name: string;
  description: string | null;
  status: "pending" | "ingesting" | "classifying" | "completed" | "failed";
  original_filename: string;
  file_size_bytes: number;
  total_pages: number | null;
  sheets_classified: number;
  sheets_failed: number;
  classification_summary: Record<string, number> | null;
  project_name: string | null;
  project_address: string | null;
  project_number: string | null;
  created_at: string;
  updated_at: string;
}

export interface TakeoffProjectDetail extends TakeoffProject {
  sheets: PlanSheet[];
}

export interface PlanSheet {
  id: string;
  project_id: string;
  page_number: number;
  sheet_type: string | null;
  classification_confidence: number | null;
  sheet_number: string | null;
  sheet_name: string | null;
  is_raster: boolean;
  thumbnail_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlanSheetDetail extends PlanSheet {
  classification_model: string | null;
  project_name: string | null;
  project_address: string | null;
  date: string | null;
  revision: string | null;
  scale: string | null;
  drawn_by: string | null;
  checked_by: string | null;
  applicable_codes: string | null;
  full_image_path: string | null;
  raw_classification: Record<string, unknown> | null;
  raw_title_block: Record<string, unknown> | null;
}

export interface TakeoffUploadResponse {
  project_id: string;
  status: string;
  message: string;
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

// ---------------------------------------------------------------------------
// V2 API functions: Contacts
// ---------------------------------------------------------------------------

export async function getContacts(params: {
  owner_id?: string;
  buying_role?: string;
  has_email?: boolean;
  skip?: number;
  limit?: number;
} = {}): Promise<Contact[]> {
  const { data } = await api.get("/contacts/", { params });
  return data;
}

export async function getContact(contactId: string): Promise<Contact> {
  const { data } = await api.get(`/contacts/${contactId}`);
  return data;
}

export async function optOutContact(
  contactId: string,
  optedOut: boolean = true
): Promise<Contact> {
  const { data } = await api.post(`/contacts/${contactId}/opt-out`, {
    opted_out: optedOut,
  });
  return data;
}

// ---------------------------------------------------------------------------
// V2 API functions: Trigger Events
// ---------------------------------------------------------------------------

export async function getTriggerEvents(params: {
  property_id?: string;
  event_type?: string;
  skip?: number;
  limit?: number;
} = {}): Promise<TriggerEvent[]> {
  const { data } = await api.get("/trigger-events/", { params });
  return data;
}

// ---------------------------------------------------------------------------
// V2 API functions: Outreach
// ---------------------------------------------------------------------------

export async function getOutreachQueue(params: {
  channel?: OutreachChannel;
  status?: string;
  campaign_id?: string;
  skip?: number;
  limit?: number;
} = {}): Promise<OutreachTouch[]> {
  const { data } = await api.get("/outreach/queue", { params });
  return data;
}

export async function getLinkedInActions(
  status: string = "pending"
): Promise<OutreachTouch[]> {
  const { data } = await api.get("/outreach/linkedin-actions", {
    params: { status },
  });
  return data;
}

export async function getCallList(
  status: string = "pending"
): Promise<OutreachTouch[]> {
  const { data } = await api.get("/outreach/call-list", {
    params: { status },
  });
  return data;
}

export async function getDirectMailQueue(
  status: string = "pending"
): Promise<OutreachTouch[]> {
  const { data } = await api.get("/outreach/direct-mail", {
    params: { status },
  });
  return data;
}

export async function updateOutreachTouch(
  touchId: string,
  payload: OutreachTouchUpdate
): Promise<OutreachTouch> {
  const { data } = await api.patch(`/outreach/${touchId}`, payload);
  return data;
}

// ---------------------------------------------------------------------------
// Takeoff API functions
// ---------------------------------------------------------------------------

export async function uploadTakeoffProject(
  file: File,
  name: string,
  description?: string
): Promise<TakeoffUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const params: Record<string, string> = { name };
  if (description) params.description = description;
  const { data } = await api.post("/takeoff/projects/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    params,
  });
  return data;
}

export async function getTakeoffProjects(
  status?: string
): Promise<TakeoffProject[]> {
  const { data } = await api.get("/takeoff/projects", {
    params: status ? { status } : {},
  });
  return data;
}

export async function getTakeoffProjectDetail(
  projectId: string
): Promise<TakeoffProjectDetail> {
  const { data } = await api.get(`/takeoff/projects/${projectId}`);
  return data;
}

export async function getProjectSheets(
  projectId: string,
  sheetType?: string
): Promise<PlanSheet[]> {
  const { data } = await api.get(`/takeoff/projects/${projectId}/sheets`, {
    params: sheetType ? { sheet_type: sheetType } : {},
  });
  return data;
}

export async function getProjectStatus(
  projectId: string
): Promise<Record<string, unknown>> {
  const { data } = await api.get(`/takeoff/projects/${projectId}/status`);
  return data;
}

export async function getSheetDetail(
  sheetId: string
): Promise<PlanSheetDetail> {
  const { data } = await api.get(`/takeoff/sheets/${sheetId}`);
  return data;
}

export async function reclassifySheet(
  sheetId: string
): Promise<PlanSheetDetail> {
  const { data } = await api.post(`/takeoff/sheets/${sheetId}/reclassify`);
  return data;
}

export function getTakeoffFileUrl(path: string): string {
  const base = import.meta.env.VITE_API_URL || "/api/v1";
  return `${base}/takeoff/files/${path}`;
}
