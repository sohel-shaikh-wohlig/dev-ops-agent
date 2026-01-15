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
      <SheetContent className="w-[520px] sm:w-[700px] overflow-y-auto">
        <SheetHeader className="mb-6">
          <SheetTitle className="text-2xl font-bold">
            {appName || "Application Details"}
          </SheetTitle>
        </SheetHeader>

        {isLoading ? (
          <div className="space-y-4">
            <div className="h-16 bg-muted animate-pulse rounded-full" />
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
            {/* Status Pills */}
            <div className="grid grid-cols-2 gap-4">
              <div
                className={`flex items-center justify-center py-3 rounded-full border ${appDetail.status.health.status === "Healthy"
                    ? "bg-green-500/10 border-green-500/20 text-green-500"
                    : "bg-yellow-500/10 border-yellow-500/20 text-yellow-500"
                  }`}
              >
                {appDetail.status.health.status === "Healthy" ? (
                  <CheckCircle2 className="w-5 h-5 mr-2" />
                ) : (
                  <AlertTriangle className="w-5 h-5 mr-2" />
                )}
                <span className="font-semibold">Health: {appDetail.status.health.status}</span>
              </div>
              <div
                className={`flex items-center justify-center py-3 rounded-full border ${appDetail.status.sync.status === "Synced"
                    ? "bg-green-500/10 border-green-500/20 text-green-500"
                    : "bg-blue-500/10 border-blue-500/20 text-blue-500"
                  }`}
              >
                {appDetail.status.sync.status === "Synced" ? (
                  <CheckCircle2 className="w-5 h-5 mr-2" />
                ) : (
                  <RefreshCw className="w-5 h-5 mr-2" />
                )}
                <span className="font-semibold">Sync: {appDetail.status.sync.status}</span>
              </div>
            </div>

            {/* Resources List */}
            <div>
              <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Box className="w-6 h-6" /> Managed Resources
              </h3>

              {appDetail.status.resources && appDetail.status.resources.length > 0 ? (
                <div className="border border-border/50 rounded-lg overflow-hidden bg-card/50">
                  {appDetail.status.resources.map((resource, i) => (
                    <div
                      key={`${resource.kind}-${resource.name}-${i}`}
                      className="p-4 flex items-center justify-between border-b border-border/50 last:border-0 hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex flex-col">
                        <span className="font-bold text-base">{resource.name}</span>
                        <span className="text-sm text-muted-foreground font-medium">
                          {resource.kind}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge
                          variant="secondary"
                          className="bg-secondary/50 hover:bg-secondary/70 px-3 py-1 rounded-full text-xs font-semibold"
                        >
                          {resource.status || "Unknown"}
                        </Badge>
                        {resource.health?.status && (
                          <Badge
                            className={`px-3 py-1 rounded-full text-xs font-semibold border ${resource.health.status === "Healthy"
                                ? "bg-green-500/10 text-green-500 border-green-500/20 hover:bg-green-500/20"
                                : "bg-yellow-500/10 text-yellow-500 border-yellow-500/20 hover:bg-yellow-500/20"
                              }`}
                            variant="outline"
                          >
                            {resource.health.status}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center p-8 border border-dashed rounded-lg text-muted-foreground">
                  No resources found
                </div>
              )}
            </div>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
