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
  type PropertyFilters,
  type PipelineStatus,
  type Campaign,
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
