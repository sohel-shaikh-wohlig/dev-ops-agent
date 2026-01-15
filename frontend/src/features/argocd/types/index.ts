// ArgoCD API types
export interface ArgoCDApplication {
    name: string;
    project: string;
    sync_status: string;
    health_status: string;
    repo_url: string;
    namespace: string;
    created_at: string;
}

export interface ArgoCDResource {
    kind: string;
    name: string;
    status: string;
    health?: { status: string };
}

export interface ArgoCDDetail {
    metadata: {
        name: string;
    };
    status: {
        sync: {
            status: string;
        };
        health: {
            status: string;
        };
        resources: ArgoCDResource[];
    };
}

// UI types for deployments
export type DeploymentStatus = "Healthy" | "Progressing" | "Degraded";
export type HealthStatus = "Healthy" | "Progressing" | "Degraded" | "Missing";
export type SyncStatus = "Synced" | "OutOfSync" | "Unknown";

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
    syncStatus: SyncStatus;
    lastSyncTime: string;
    repository: string;
    path: string;
}
