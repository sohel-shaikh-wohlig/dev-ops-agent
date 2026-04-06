import { apiClient } from "@/services/api-client";
import type { ArgoCDApplication, ArgoCDDetail, Deployment } from "../types";

export const fetchApplications = async (): Promise<ArgoCDApplication[]> => {
    const response = await apiClient.get<{ items: ArgoCDApplication[] }>('/argocd/applications');
    return response.items;
};

export const fetchApplicationDetails = async (appName: string): Promise<ArgoCDDetail> => {
    const response = await apiClient.get<ArgoCDDetail>(`/argocd/applications/${appName}`);
    return response;
};

export const createApplication = async (
    request: import("../types").CreateApplicationRequest,
    env?: string
) => {
    let endpoint = '/argocd/applications';
    if (env) {
        endpoint += `?env=${env}`;
    }
    return apiClient.post<{ message?: string; }>(endpoint, request);
};

// Helper to map API response to Deployment type expected by DeploymentCard
export const mapArgoCDAppToDeployment = (app: ArgoCDApplication): Deployment => {
    return {
        id: app.name,
        name: app.name,
        namespace: app.namespace,
        cluster: { name: "default", server: "https://kubernetes.default.svc" },
        status: app.health_status as Deployment['status'],
        health: app.health_status as Deployment['health'],
        syncStatus: app.sync_status as Deployment['syncStatus'],
        lastSyncTime: app.created_at,
        repository: app.repo_url,
        path: "n/a",
    };
};
