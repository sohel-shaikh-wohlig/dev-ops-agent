import { Loader2 } from "lucide-react";
import { DeploymentCard } from "@/features/argocd";
import { useGitOpsData } from "@/hooks/useGitOpsData";

export function Dashboard() {
    const { deployments, loading } = useGitOpsData();

    return (
        <main className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto">
                <div className="mb-6">
                    <h2 className="text-xl font-semibold text-foreground">Active Deployments</h2>
                    <p className="text-sm text-muted-foreground mt-1">
                        Monitor and manage your GitOps deployments across all clusters
                    </p>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center h-64">
                        <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {deployments.map((deployment) => (
                            <DeploymentCard key={deployment.id} deployment={deployment} />
                        ))}
                    </div>
                )}
            </div>
        </main>
    );
}
