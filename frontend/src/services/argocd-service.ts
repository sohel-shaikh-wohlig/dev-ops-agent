import { apiClient } from "./api-client";

export interface ArgoCDApplication {
    name: string;
    project: string;
    sync_status: string;
    health_status: string;
    repo_url: string;
    namespace: string;
    created_at: string;
}

export const fetchApplications = async (): Promise<ArgoCDApplication[]> => {
    const response = await apiClient.get<{ items: ArgoCDApplication[] }>('/argocd/applications');
    return response.items;
};

// Helper to map API response to Deployment type expected by DeploymentCard
// We need to adapt the API interfaces to match the frontend types if they differ significantly.
// Looking at DeploymentCard:
// interface Deployment {
//     id: string;
//     name: string;
//     namespace: string;
//     cluster: { name: string; server: string };
//     status: DeploymentStatus; // "Healthy" | "Progressing" | "Degraded"
//     health: string;
//     syncStatus: string; // "Synced" | "OutOfSync" -> API returns sync_status
//     lastSyncTime: string;
//     repository: string;
//     path: string;
// }

export const mapArgoCDAppToDeployment = (app: ArgoCDApplication): any => {
    return {
        id: app.name, // Using name as ID for now
        name: app.name,
        namespace: app.namespace,
        cluster: { name: "default", server: "https://kubernetes.default.svc" }, // API doesn't seem to provide cluster info in the simplified schema?
        status: app.health_status,
        health: app.health_status,
        syncStatus: app.sync_status,
        lastSyncTime: app.created_at, // Using created_at as placeholder or we need another field?
        repository: app.repo_url,
        path: "n/a",
    };
};
