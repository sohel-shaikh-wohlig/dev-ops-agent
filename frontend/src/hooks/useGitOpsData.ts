import { useQuery } from '@tanstack/react-query';
import type { Deployment, DeploymentStatus } from "@/features/argocd";

const MOCK_DEPLOYMENTS: Deployment[] = [
    {
        id: "1",
        name: "frontend-app",
        namespace: "production",
        cluster: { name: "prod-us-east-1", server: "https://prod-cluster-1.example.com" },
        status: "Healthy",
        health: "Healthy",
        syncStatus: "Synced",
        lastSyncTime: "2 minutes ago",
        repository: "https://github.com/company/frontend-app",
        path: "k8s/overlays/production",
    },
    {
        id: "2",
        name: "api-gateway",
        namespace: "production",
        cluster: { name: "prod-us-east-1", server: "https://prod-cluster-1.example.com" },
        status: "Progressing",
        health: "Progressing",
        syncStatus: "Synced",
        lastSyncTime: "5 minutes ago",
        repository: "https://github.com/company/api-gateway",
        path: "k8s/overlays/production",
    },
    {
        id: "3",
        name: "auth-service",
        namespace: "production",
        cluster: { name: "prod-us-west-2", server: "https://prod-cluster-2.example.com" },
        status: "Healthy",
        health: "Healthy",
        syncStatus: "Synced",
        lastSyncTime: "1 minute ago",
        repository: "https://github.com/company/auth-service",
        path: "k8s/overlays/production",
    },
    {
        id: "4",
        name: "payment-processor",
        namespace: "production",
        cluster: { name: "prod-us-east-1", server: "https://prod-cluster-1.example.com" },
        status: "Degraded",
        health: "Degraded",
        syncStatus: "OutOfSync",
        lastSyncTime: "15 minutes ago",
        repository: "https://github.com/company/payment-processor",
        path: "k8s/overlays/production",
    },
    {
        id: "5",
        name: "notification-service",
        namespace: "staging",
        cluster: { name: "staging-us-east-1", server: "https://staging-cluster.example.com" },
        status: "Healthy",
        health: "Healthy",
        syncStatus: "Synced",
        lastSyncTime: "3 minutes ago",
        repository: "https://github.com/company/notification-service",
        path: "k8s/overlays/staging",
    },
    {
        id: "6",
        name: "analytics-engine",
        namespace: "production",
        cluster: { name: "prod-us-west-2", server: "https://prod-cluster-2.example.com" },
        status: "Healthy",
        health: "Healthy",
        syncStatus: "Synced",
        lastSyncTime: "7 minutes ago",
        repository: "https://github.com/company/analytics-engine",
        path: "k8s/overlays/production",
    },
    {
        id: "7",
        name: "user-service",
        namespace: "production",
        cluster: { name: "prod-us-east-1", server: "https://prod-cluster-1.example.com" },
        status: "Progressing",
        health: "Progressing",
        syncStatus: "Synced",
        lastSyncTime: "4 minutes ago",
        repository: "https://github.com/company/user-service",
        path: "k8s/overlays/production",
    },
    {
        id: "8",
        name: "inventory-service",
        namespace: "production",
        cluster: { name: "prod-us-west-2", server: "https://prod-cluster-2.example.com" },
        status: "Healthy",
        health: "Healthy",
        syncStatus: "Synced",
        lastSyncTime: "6 minutes ago",
        repository: "https://github.com/company/inventory-service",
        path: "k8s/overlays/production",
    },
    {
        id: "9",
        name: "search-indexer",
        namespace: "production",
        cluster: { name: "prod-us-east-1", server: "https://prod-cluster-1.example.com" },
        status: "Healthy",
        health: "Healthy",
        syncStatus: "Synced",
        lastSyncTime: "8 minutes ago",
        repository: "https://github.com/company/search-indexer",
        path: "k8s/overlays/production",
    },
    {
        id: "10",
        name: "email-worker",
        namespace: "staging",
        cluster: { name: "staging-us-east-1", server: "https://staging-cluster.example.com" },
        status: "Progressing",
        health: "Progressing",
        syncStatus: "Synced",
        lastSyncTime: "2 minutes ago",
        repository: "https://github.com/company/email-worker",
        path: "k8s/overlays/staging",
    },
];

const randomStatus = (): DeploymentStatus => {
    const statuses: DeploymentStatus[] = ["Healthy", "Progressing", "Degraded"];
    return statuses[Math.floor(Math.random() * statuses.length)];
};

const fetchDeployments = async (): Promise<Deployment[]> => {
    // Simulate initial loading delay
    await new Promise((resolve) => setTimeout(resolve, 1000));
    return MOCK_DEPLOYMENTS.map(d => {
        // Randomly update some deployments to simulate real-time status
        if (Math.random() > 0.7) {
            const newStatus = randomStatus();
            return {
                ...d,
                status: newStatus,
                health: newStatus,
                lastSyncTime: "Just now",
            };
        }
        return d;
    });
};

export function useGitOpsData() {
    const { data: deployments = [], isLoading: loading } = useQuery({
        queryKey: ['deployments'],
        queryFn: fetchDeployments,
        refetchInterval: 5000,
    });

    return { deployments, loading };
}
