import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "./StatusBadge";
import type { Deployment } from "@/types/gitops";
import { Server, GitBranch, Clock } from "lucide-react";

interface DeploymentCardProps {
    deployment: Deployment;
}

export function DeploymentCard({ deployment }: DeploymentCardProps) {
    return (
        <Card className="hover:shadow-md transition-all duration-300 hover:scale-[1.02] border-border bg-card">
            <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                    <div className="space-y-1">
                        <CardTitle className="text-base font-semibold text-foreground">{deployment.name}</CardTitle>
                        <p className="text-xs font-medium text-muted-foreground">{deployment.namespace}</p>
                    </div>
                    <StatusBadge status={deployment.status} />
                </div>
            </CardHeader>
            <CardContent className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                    <Server className="w-4 h-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Cluster:</span>
                    <span className="font-medium text-foreground">{deployment.cluster.name}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                    <GitBranch className="w-4 h-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Sync:</span>
                    <span
                        className={`font-medium ${deployment.syncStatus === "Synced"
                            ? "text-green-500 dark:text-green-400"
                            : deployment.syncStatus === "OutOfSync"
                                ? "text-destructive dark:text-red-400"
                                : "text-yellow-600 dark:text-yellow-400"
                            }`}
                    >
                        {deployment.syncStatus}
                    </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                    <Clock className="w-4 h-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Last sync:</span>
                    <span className="font-medium text-foreground">{deployment.lastSyncTime}</span>
                </div>
            </CardContent>
        </Card>
    );
}
