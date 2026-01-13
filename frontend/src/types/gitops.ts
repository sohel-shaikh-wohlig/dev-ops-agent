export type DeploymentStatus = "Healthy" | "Progressing" | "Degraded";
export type HealthStatus = "Healthy" | "Progressing" | "Degraded" | "Missing";

export interface ClusterInfo {
    name: string;
    server: string;
}

export interface Deployment {
    id: string;
    name: string;
    namespace: string;
    cluster: ClusterInfo;
    status: DeploymentStatus;
    health: HealthStatus;
    syncStatus: "Synced" | "OutOfSync" | "Unknown";
    lastSyncTime: string;
    repository: string;
    path: string;
}
