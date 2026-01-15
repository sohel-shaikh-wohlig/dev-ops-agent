import { Badge } from "@/components/ui/badge";
import type { DeploymentStatus } from "../types";
import { AlertCircle, Loader2 } from "lucide-react";

interface StatusBadgeProps {
    status: DeploymentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
    const getVariantAndIcon = () => {
        switch (status) {
            case "Healthy":
                return {
                    variant: "success" as const,
                    icon: (
                        <div className="relative flex h-2 w-2 mr-1">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                        </div>
                    ),
                };
            case "Progressing":
                return {
                    variant: "warning" as const,
                    icon: <Loader2 className="w-3 h-3 animate-spin" />,
                };
            case "Degraded":
                return {
                    variant: "error" as const,
                    icon: <AlertCircle className="w-3 h-3" />,
                };
            default:
                return {
                    variant: "secondary" as const,
                    icon: <AlertCircle className="w-3 h-3" />,
                };
        }
    };

    const { variant, icon } = getVariantAndIcon();

    return (
        <Badge variant={variant} className="flex items-center gap-1">
            {icon}
            {status}
        </Badge>
    );
}
