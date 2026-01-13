import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "./StatusBadge";
import type { Deployment } from "@/types/gitops";
import { Server, GitBranch, Clock } from "lucide-react";

interface DeploymentCardProps {
    deployment: Deployment;
}

export function DeploymentCard({ deployment }: DeploymentCardProps) {
    return (
        <Card className="hover:shadow-md transition-all duration-300 hover:scale-[1.02] border-gray-200 bg-white">
            <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                    <div className="space-y-1">
                        <CardTitle className="text-base font-semibold text-gray-900">{deployment.name}</CardTitle>
                        <p className="text-xs font-medium text-gray-500">{deployment.namespace}</p>
                    </div>
                    <StatusBadge status={deployment.status} />
                </div>
            </CardHeader>
            <CardContent className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                    <Server className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-500">Cluster:</span>
                    <span className="font-medium text-gray-900">{deployment.cluster.name}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                    <GitBranch className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-500">Sync:</span>
                    <span
                        className={`font-medium ${deployment.syncStatus === "Synced"
                            ? "text-green-600"
                            : deployment.syncStatus === "OutOfSync"
                                ? "text-red-600"
                                : "text-yellow-600"
                            }`}
                    >
                        {deployment.syncStatus}
                    </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-500">Last sync:</span>
                    <span className="font-medium text-gray-900">{deployment.lastSyncTime}</span>
                </div>
            </CardContent>
        </Card>
    );
}
