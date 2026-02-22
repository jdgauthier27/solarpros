import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getProperties,
  getPropertyDetail,
  getPropertyMap,
  getScores,
  getScoreDistribution,
  getCampaigns,
  getCampaignMetrics,
  getPipelineStatus,
  getAgentRuns,
  getDashboardOverview,
  getDashboardFunnel,
  startPipeline,
  createCampaign,
  pauseCampaign,
  resumeCampaign,
  getContacts,
  getContact,
  optOutContact,
  getTriggerEvents,
  getOutreachQueue,
  getLinkedInActions,
  getCallList,
  getDirectMailQueue,
  updateOutreachTouch,
  getTakeoffProjects,
  getTakeoffProjectDetail,
  uploadTakeoffProject,
  reclassifySheet,
  type PropertyFilters,
  type PipelineStatus,
  type Campaign,
  type OutreachTouch,
  type OutreachTouchUpdate,
  type OutreachChannel,
  type TakeoffUploadResponse,
  type PlanSheetDetail,
} from "../api/client";

// ---------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------

export function useProperties(filters: PropertyFilters = {}) {
  return useQuery({
    queryKey: ["properties", filters],
    queryFn: () => getProperties(filters),
  });
}

export function usePropertyDetail(id: string | null) {
  return useQuery({
    queryKey: ["property", id],
    queryFn: () => getPropertyDetail(id!),
    enabled: !!id,
  });
}

export function usePropertyMap(county?: string) {
  return useQuery({
    queryKey: ["propertyMap", county],
    queryFn: () => getPropertyMap(county),
  });
}

// ---------------------------------------------------------------------------
// Scores
// ---------------------------------------------------------------------------

export function useScores(params: Record<string, string | number> = {}) {
  return useQuery({
    queryKey: ["scores", params],
    queryFn: () => getScores(params),
  });
}

export function useScoreDistribution() {
  return useQuery({
    queryKey: ["scoreDistribution"],
    queryFn: getScoreDistribution,
  });
}

// ---------------------------------------------------------------------------
// Campaigns
// ---------------------------------------------------------------------------

export function useCampaigns() {
  return useQuery({
    queryKey: ["campaigns"],
    queryFn: getCampaigns,
  });
}

export function useCampaignMetrics(campaignId: string | null) {
  return useQuery({
    queryKey: ["campaignMetrics", campaignId],
    queryFn: () => getCampaignMetrics(campaignId!),
    enabled: !!campaignId,
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createCampaign,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

export function usePauseCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (campaignId: string) => pauseCampaign(campaignId),
    onSuccess: (_data: Campaign) => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

export function useResumeCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (campaignId: string) => resumeCampaign(campaignId),
    onSuccess: (_data: Campaign) => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

// ---------------------------------------------------------------------------
// Pipeline / Agents
// ---------------------------------------------------------------------------

export function usePipelineStatus(isRunning: boolean) {
  return useQuery({
    queryKey: ["pipelineStatus"],
    queryFn: () => getPipelineStatus(),
    refetchInterval: isRunning ? 5000 : false,
  });
}

export function useStartPipeline() {
  return useMutation({
    mutationFn: (payload: { counties: string[]; use_mock: boolean }) =>
      startPipeline(payload),
    onSuccess: (_data: PipelineStatus) => {
      // caller should capture pipeline id from response
    },
  });
}

export function useAgentRuns(isRunning?: boolean) {
  return useQuery({
    queryKey: ["agentRuns"],
    queryFn: () => getAgentRuns(),
    refetchInterval: isRunning ? 5000 : false,
  });
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export function useDashboardOverview() {
  return useQuery({
    queryKey: ["dashboardOverview"],
    queryFn: getDashboardOverview,
  });
}

export function useDashboardFunnel() {
  return useQuery({
    queryKey: ["dashboardFunnel"],
    queryFn: getDashboardFunnel,
  });
}

// ---------------------------------------------------------------------------
// V2: Contacts
// ---------------------------------------------------------------------------

export function useContacts(params: {
  owner_id?: string;
  buying_role?: string;
  has_email?: boolean;
} = {}) {
  return useQuery({
    queryKey: ["contacts", params],
    queryFn: () => getContacts(params),
  });
}

export function useContact(contactId: string | null) {
  return useQuery({
    queryKey: ["contact", contactId],
    queryFn: () => getContact(contactId!),
    enabled: !!contactId,
  });
}

export function useOptOutContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ contactId, optedOut }: { contactId: string; optedOut: boolean }) =>
      optOutContact(contactId, optedOut),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
    },
  });
}

// ---------------------------------------------------------------------------
// V2: Trigger Events
// ---------------------------------------------------------------------------

export function useTriggerEvents(params: {
  property_id?: string;
  event_type?: string;
} = {}) {
  return useQuery({
    queryKey: ["triggerEvents", params],
    queryFn: () => getTriggerEvents(params),
  });
}

// ---------------------------------------------------------------------------
// V2: Outreach
// ---------------------------------------------------------------------------

export function useOutreachQueue(params: {
  channel?: OutreachChannel;
  status?: string;
  campaign_id?: string;
} = {}) {
  return useQuery({
    queryKey: ["outreachQueue", params],
    queryFn: () => getOutreachQueue(params),
  });
}

export function useLinkedInActions(status: string = "pending") {
  return useQuery({
    queryKey: ["linkedInActions", status],
    queryFn: () => getLinkedInActions(status),
  });
}

export function useCallList(status: string = "pending") {
  return useQuery({
    queryKey: ["callList", status],
    queryFn: () => getCallList(status),
  });
}

export function useDirectMailQueue(status: string = "pending") {
  return useQuery({
    queryKey: ["directMailQueue", status],
    queryFn: () => getDirectMailQueue(status),
  });
}

export function useUpdateOutreachTouch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ touchId, payload }: { touchId: string; payload: OutreachTouchUpdate }) =>
      updateOutreachTouch(touchId, payload),
    onSuccess: (_data: OutreachTouch) => {
      qc.invalidateQueries({ queryKey: ["outreachQueue"] });
      qc.invalidateQueries({ queryKey: ["linkedInActions"] });
      qc.invalidateQueries({ queryKey: ["callList"] });
      qc.invalidateQueries({ queryKey: ["directMailQueue"] });
    },
  });
}

// ---------------------------------------------------------------------------
// Takeoff
// ---------------------------------------------------------------------------

export function useTakeoffProjects(status?: string) {
  return useQuery({
    queryKey: ["takeoffProjects", status],
    queryFn: () => getTakeoffProjects(status),
  });
}

export function useTakeoffProjectDetail(projectId: string | null) {
  return useQuery({
    queryKey: ["takeoffProject", projectId],
    queryFn: () => getTakeoffProjectDetail(projectId!),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "pending" || status === "ingesting" || status === "classifying") {
        return 3000;
      }
      return false;
    },
  });
}

export function useUploadTakeoff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      name,
      description,
    }: {
      file: File;
      name: string;
      description?: string;
    }) => uploadTakeoffProject(file, name, description),
    onSuccess: (_data: TakeoffUploadResponse) => {
      qc.invalidateQueries({ queryKey: ["takeoffProjects"] });
    },
  });
}

export function useReclassifySheet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sheetId: string) => reclassifySheet(sheetId),
    onSuccess: (_data: PlanSheetDetail) => {
      qc.invalidateQueries({ queryKey: ["takeoffProject"] });
    },
  });
}
