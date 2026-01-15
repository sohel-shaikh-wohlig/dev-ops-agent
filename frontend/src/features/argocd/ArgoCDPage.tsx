import { useQuery } from '@tanstack/react-query';
import { fetchApplications, mapArgoCDAppToDeployment } from "./services/argocd-service";
import { DeploymentCard } from "./components/DeploymentCard";
import { Loader2, RefreshCw, CheckCircle2, AlertTriangle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApplicationSidebar } from "./components/ApplicationSidebar";
import { useState } from "react";

export function ArgoCDPage() {
    const [selectedAppName, setSelectedAppName] = useState<string | null>(null);
    const { data: deployments = [], isLoading, error, refetch } = useQuery({
        queryKey: ['argocd-applications'],
        queryFn: async () => {
            const apps = await fetchApplications();
            return apps.map(mapArgoCDAppToDeployment);
        },
        refetchInterval: 30000,
    });

    // Derived Stats
    const totalApps = deployments.length;
    const healthyApps = deployments.filter(d => d.health === 'Healthy').length;
    const outOfSyncApps = deployments.filter(d => d.syncStatus === 'OutOfSync').length;

    const handleAppClick = (app: any) => {
        setSelectedAppName(app.name);
    };

    if (isLoading && deployments.length === 0) {
        return (
            <div className="flex items-center justify-center h-full">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Error loading applications</AlertTitle>
                    <AlertDescription className="mt-2 flex flex-col gap-4">
                        <p>{error instanceof Error ? error.message : 'Unknown error occurred while fetching ArgoCD data.'}</p>
                        <Button variant="outline" onClick={() => refetch()} className="w-fit">
                            <RefreshCw className="mr-2 h-4 w-4" /> Try Again
                        </Button>
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    return (
        <main className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto space-y-6">

                {/* Stats Section */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Total Applications</CardTitle>
                            <div className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{totalApps}</div>
                            <p className="text-xs text-muted-foreground">Managed by ArgoCD</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Healthy</CardTitle>
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{healthyApps}</div>
                            <p className="text-xs text-muted-foreground">Applications in healthy state</p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Out of Sync</CardTitle>
                            <AlertTriangle className="h-4 w-4 text-yellow-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{outOfSyncApps}</div>
                            <p className="text-xs text-muted-foreground">Applications requiring sync</p>
                        </CardContent>
                    </Card>
                </div>

                <div className="mb-6">
                    <h2 className="text-xl font-semibold text-foreground">ArgoCD Applications</h2>
                    <p className="text-sm text-muted-foreground mt-1">
                        Monitor and manage your GitOps deployments across all clusters
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {deployments.map((deployment) => (
                        <DeploymentCard
                            key={deployment.id}
                            deployment={deployment}
                            onClick={handleAppClick}
                        />
                    ))}
                </div>
            </div>

            <ApplicationSidebar
                open={!!selectedAppName}
                onOpenChange={(open) => !open && setSelectedAppName(null)}
                appName={selectedAppName}
            />
        </main>
    );
}
