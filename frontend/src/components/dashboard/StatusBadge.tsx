import { Badge } from "@/components/ui/badge";
import type { DeploymentStatus } from "@/types/gitops";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

interface StatusBadgeProps {
    status: DeploymentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
    const getVariantAndIcon = () => {
        switch (status) {
            case "Healthy":
                return {
                    variant: "success" as const,
                    icon: <CheckCircle2 className="w-3 h-3" />,
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
