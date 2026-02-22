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

export function useScores(filters: PropertyFilters = {}) {
  return useQuery({
    queryKey: ["scores", filters],
    queryFn: () => getScores(filters),
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

export function usePipelineStatus(pipelineId: string | null, isRunning: boolean) {
  return useQuery({
    queryKey: ["pipelineStatus", pipelineId],
    queryFn: () => getPipelineStatus(pipelineId!),
    enabled: !!pipelineId,
    refetchInterval: isRunning ? 5000 : false,
  });
}

export function useStartPipeline() {
  return useMutation({
    mutationFn: (county: string) => startPipeline(county),
    onSuccess: (_data: PipelineStatus) => {
      // caller should capture pipeline id from response
    },
  });
}

export function useAgentRuns(pipelineId?: string, isRunning?: boolean) {
  return useQuery({
    queryKey: ["agentRuns", pipelineId],
    queryFn: () => getAgentRuns(pipelineId),
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
