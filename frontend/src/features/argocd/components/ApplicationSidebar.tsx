import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { useQuery } from "@tanstack/react-query";
import { fetchApplicationDetails } from "../services/argocd-service";
import { AlertTriangle, RefreshCw, CheckCircle2, Box } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

interface ApplicationSidebarProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  appName: string | null;
}

export function ApplicationSidebar({
  open,
  onOpenChange,
  appName,
}: ApplicationSidebarProps) {
  const {
    data: appDetail,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["argocd-application", appName],
    queryFn: () => fetchApplicationDetails(appName!),
    enabled: !!appName && open,
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
        <SheetHeader className="mb-6">
          <SheetTitle className="text-2xl font-bold">
            {appName || "Application Details"}
          </SheetTitle>
        </SheetHeader>

        {isLoading ? (
          <div className="space-y-4">
            <div className="h-20 bg-muted animate-pulse rounded-lg" />
            <div className="h-64 bg-muted animate-pulse rounded-lg" />
          </div>
        ) : error ? (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Error fetching details</AlertTitle>
            <AlertDescription className="mt-2 flex flex-col gap-4">
              <p>{error instanceof Error ? error.message : "Unknown error"}</p>
              <Button
                variant="outline"
                onClick={() => refetch()}
                className="w-fit"
              >
                <RefreshCw className="mr-2 h-4 w-4" /> Retry
              </Button>
            </AlertDescription>
          </Alert>
        ) : appDetail ? (
          <div className="space-y-8">
            {/* Summary Badges */}
            <div className="flex gap-4">
              <Badge
                variant={
                  appDetail.status.health.status === "Healthy"
                    ? "success"
                    : "secondary"
                }
                className="flex-1 justify-center py-2 text-sm"
              >
                {appDetail.status.health.status === "Healthy" && (
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                )}
                Health: {appDetail.status.health.status}
              </Badge>
              <Badge
                variant={
                  appDetail.status.sync.status === "Synced"
                    ? "default"
                    : "warning"
                }
                className="flex-1 justify-center py-2 text-sm"
              >
                {appDetail.status.sync.status === "OutOfSync" && (
                  <RefreshCw className="w-4 h-4 mr-2" />
                )}
                Sync: {appDetail.status.sync.status}
              </Badge>
            </div>

            {/* Resources List */}
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Box className="w-5 h-5" /> Managed Resources
              </h3>
              <div className="border rounded-lg divide-y">
                {appDetail.status.resources.map((resource, i) => (
                  <div
                    key={`${resource.kind}-${resource.name}-${i}`}
                    className="p-4 flex items-center justify-between hover:bg-muted/50 transition-colors"
                  >
                    <div>
                      <p className="font-medium text-sm">{resource.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {resource.kind}
                      </p>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {resource.status || "Unknown"}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
