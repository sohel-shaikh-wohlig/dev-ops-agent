import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "@tanstack/react-form";
import {
  fetchApplications,
  mapArgoCDAppToDeployment,
  createApplication
} from "./services/argocd-service";
import { DeploymentCard } from "./components/DeploymentCard";
import {
  Loader2,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Ban,
  Plus,
  ArrowLeft,
  AlertCircle
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter, CardDescription } from "@/components/ui/card";
import { ApplicationSidebar } from "./components/ApplicationSidebar";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { ApiError } from "@/services/api-client";

export function ArgoCDPage() {
  const [viewMode, setViewMode] = useState<'list' | 'create'>('list');
  const [selectedAppName, setSelectedAppName] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const {
    data: deployments = [],
    isLoading: isQueryLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["argocd-applications"],
    queryFn: async () => {
      const apps = await fetchApplications();
      return apps.map(mapArgoCDAppToDeployment);
    },
    refetchInterval: 30000,
  });

  const [isCreating, setIsCreating] = useState(false);
  const [apiError, setApiError] = useState<{
    status?: string;
    message?: string;
    detail?: any;
  } | null>(null);

  const form = useForm({
    defaultValues: {
      env: "dev",
      name: "",
      project: "default",
      repo_url: "",
      path: ".",
      target_revision: "HEAD",
      destination_namespace: "default",
      auto_sync: false,
      auto_prune: false,
      self_heal: false,
    },
    validators: {
      onSubmit: ({ value }) => {
        if (!value.name) return "Application name is required";
        if (!value.repo_url) return "Git repository URL is required";
        return undefined;
      },
    },
    onSubmit: async ({ value }) => {
      setIsCreating(true);
      setApiError(null);
      try {
        const { env, ...requestPayload } = value;
        await createApplication(requestPayload, env);
        toast.success("Application Created", { description: "ArgoCD application created successfully." });
        form.reset();
        setViewMode('list');
        queryClient.invalidateQueries({ queryKey: ["argocd-applications"] });
      } catch (error) {
        if (error instanceof ApiError) {
          if (error.data && error.data.detail) {
             setApiError(error.data);
          } else {
             setApiError({ message: error.message });
          }
        } else {
           if (!apiError) {
              setApiError({ message: "Could not create application." });
           }
        }
        console.error(error);
      } finally {
        setIsCreating(false);
      }
    },
  });

  // Derived Stats
  const totalApps = deployments.length;
  const healthyApps = deployments.filter((d) => d.health === "Healthy").length;
  const outOfSyncApps = deployments.filter(
    (d) => d.syncStatus === "OutOfSync"
  ).length;
  const missingApps = deployments.filter((d) => d.health === "Missing").length;

  const handleAppClick = (app: any) => {
    setSelectedAppName(app.name);
  };

  if (isQueryLoading && deployments.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error && viewMode === 'list') {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error loading applications</AlertTitle>
          <AlertDescription className="mt-2 flex flex-col gap-4">
            <p>
              {error instanceof Error
                ? error.message
                : "Unknown error occurred while fetching ArgoCD data."}
            </p>
            <Button
              variant="outline"
              onClick={() => refetch()}
              className="w-fit"
            >
              <RefreshCw className="mr-2 h-4 w-4" /> Try Again
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <main className="flex-1 overflow-y-auto p-6 flex justify-center w-full">
      <div className="w-full max-w-7xl space-y-6">
        {viewMode === 'list' && (
          <div className="animate-in fade-in slide-in-from-bottom-5">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-foreground">
                  ArgoCD Applications
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Monitor and manage your deployments across all clusters
                </p>
              </div>
              <Button onClick={() => setViewMode('create')}>
                <Plus className="w-4 h-4 mr-2" />
                Create
              </Button>
            </div>

            {/* Stats Section */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Total Applications
                  </CardTitle>
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
                  <CheckCircle2 className="h-8 w-8 text-green-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{healthyApps}</div>
                  <p className="text-xs text-muted-foreground">
                    Applications in healthy state
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Out of Sync</CardTitle>
                  <AlertTriangle className="h-8 w-8 text-yellow-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{outOfSyncApps}</div>
                  <p className="text-xs text-muted-foreground">
                    Applications requiring sync
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Missing</CardTitle>
                  <Ban className="h-8 w-8 text-red-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{missingApps}</div>
                  <p className="text-xs text-muted-foreground">
                    Applications status missing
                  </p>
                </CardContent>
              </Card>
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
        )}

        {viewMode === 'create' && (
          <Card className="w-full max-w-4xl mx-auto animate-in fade-in slide-in-from-left-5">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6 border-b mb-6">
              <div className="flex items-center gap-2">
                 <div className="p-2 bg-primary/10 rounded-lg">
                    <Plus className="w-6 h-6 text-primary" />
                 </div>
                 <div>
                    <CardTitle>Create ArgoCD Application</CardTitle>
                    <CardDescription>Configure a new deployment via ArgoCD</CardDescription>
                 </div>
              </div>
              <Button variant="outline" onClick={() => {
                  setViewMode('list');
                  form.reset();
                  setApiError(null);
               }}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to List
              </Button>
            </CardHeader>
            <CardContent>
               {apiError && (
                 <Alert
                   variant="destructive"
                   className="mb-6 bg-red-500/10 text-red-600 dark:text-red-400 [&>svg]:text-red-600 dark:[&>svg]:text-red-400 border-red-500/50"
                 >
                   <AlertCircle className="h-4 w-4" />
                   <AlertTitle>{apiError.message || "Error"}</AlertTitle>
                   <AlertDescription>
                     {apiError.detail ? (
                       Array.isArray(apiError.detail) ? (
                         <ul className="list-disc list-inside space-y-1 mt-2">
                           {apiError.detail.map((err: any, index: number) => (
                             <li key={index}>
                               <span className="font-semibold">{err.loc?.[1] || "Error"}:</span>{" "}
                               {err.msg}
                             </li>
                           ))}
                         </ul>
                       ) : (
                         <p className="mt-2">{String(apiError.detail)}</p>
                       )
                     ) : (
                       <p>Something went wrong.</p>
                     )}
                   </AlertDescription>
                 </Alert>
               )}

               <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    form.handleSubmit();
                  }}
                  className="space-y-6"
                >
                  <div className="grid grid-cols-2 gap-4">
                    <form.Field
                      name="env"
                      children={(field) => (
                        <div className="space-y-2">
                          <Label htmlFor={field.name}>Environment</Label>
                          <Select
                            value={field.state.value}
                            onValueChange={(val) => field.handleChange(val)}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select environment" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="dev">Dev</SelectItem>
                              <SelectItem value="test">Test</SelectItem>
                              <SelectItem value="uat">Stage</SelectItem>
                              <SelectItem value="prod">Prod</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      )}
                    />

                    <form.Field
                      name="name"
                      children={(field) => (
                        <div className="space-y-2">
                          <Label htmlFor={field.name}>Application Name</Label>
                          <Input
                            id={field.name}
                            value={field.state.value}
                            onChange={(e) => field.handleChange(e.target.value)}
                            placeholder="e.g. user-service-dev"
                          />
                        </div>
                      )}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <form.Field
                      name="project"
                      children={(field) => (
                        <div className="space-y-2">
                          <Label htmlFor={field.name}>Project</Label>
                          <Input
                            id={field.name}
                            value={field.state.value}
                            onChange={(e) => field.handleChange(e.target.value)}
                            placeholder="default"
                          />
                        </div>
                      )}
                    />

                    <form.Field
                      name="repo_url"
                      children={(field) => (
                        <div className="space-y-2">
                          <Label htmlFor={field.name}>Git Repository URL</Label>
                          <Input
                            id={field.name}
                            value={field.state.value}
                            onChange={(e) => field.handleChange(e.target.value)}
                            placeholder="https://github.com/org/repo.git"
                          />
                        </div>
                      )}
                    />
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4">
                    <form.Field
                      name="path"
                      children={(field) => (
                        <div className="space-y-2">
                          <Label htmlFor={field.name}>Path in Repo</Label>
                          <Input
                            id={field.name}
                            value={field.state.value}
                            onChange={(e) => field.handleChange(e.target.value)}
                            placeholder="."
                          />
                        </div>
                      )}
                    />
                    <form.Field
                      name="target_revision"
                      children={(field) => (
                        <div className="space-y-2">
                          <Label htmlFor={field.name}>Target Revision</Label>
                          <Input
                            id={field.name}
                            value={field.state.value}
                            onChange={(e) => field.handleChange(e.target.value)}
                            placeholder="HEAD"
                          />
                        </div>
                      )}
                    />
                    <form.Field
                      name="destination_namespace"
                      children={(field) => (
                        <div className="space-y-2">
                          <Label htmlFor={field.name}>Dest. Namespace</Label>
                          <Input
                            id={field.name}
                            value={field.state.value}
                            onChange={(e) => field.handleChange(e.target.value)}
                            placeholder="default"
                          />
                        </div>
                      )}
                    />
                  </div>

                  <div className="flex flex-col space-y-4 pt-4 border-t">
                    <Label className="text-base font-semibold">Sync Options</Label>
                    <div className="flex space-x-8">
                       <form.Field
                         name="auto_sync"
                         children={(field) => (
                           <div className="flex items-center space-x-2">
                             <Switch
                               id={field.name}
                               checked={field.state.value}
                               onCheckedChange={field.handleChange}
                             />
                             <Label htmlFor={field.name} className="cursor-pointer">Auto Sync</Label>
                           </div>
                         )}
                       />
                       <form.Field
                         name="auto_prune"
                         children={(field) => (
                           <div className="flex items-center space-x-2">
                             <Switch
                               id={field.name}
                               checked={field.state.value}
                               onCheckedChange={field.handleChange}
                             />
                             <Label htmlFor={field.name} className="cursor-pointer">Auto Prune</Label>
                           </div>
                         )}
                       />
                       <form.Field
                         name="self_heal"
                         children={(field) => (
                           <div className="flex items-center space-x-2">
                             <Switch
                               id={field.name}
                               checked={field.state.value}
                               onCheckedChange={field.handleChange}
                             />
                             <Label htmlFor={field.name} className="cursor-pointer">Self Heal</Label>
                           </div>
                         )}
                       />
                    </div>
                  </div>

                  {/* Form Level Errors */}
                  <form.Subscribe
                    selector={(state) => state.errors}
                    children={(errors) =>
                      errors.length > 0 ? (
                        <Alert
                          variant="destructive"
                          className="bg-red-500/10 text-red-600 dark:text-red-400 [&>svg]:text-red-600 dark:[&>svg]:text-red-400 border-red-500/50"
                        >
                          <AlertCircle className="h-4 w-4" />
                          <AlertTitle>Validation Error</AlertTitle>
                          <AlertDescription>
                            {errors.map((e) => (
                              <p key={e as string}>{e as string}</p>
                            ))}
                          </AlertDescription>
                        </Alert>
                      ) : null
                    }
                  />

                  <div className="pt-4 border-t flex justify-end">
                    <form.Subscribe
                      selector={(state) => [state.canSubmit, state.isSubmitting]}
                      children={([canSubmit]) => (
                        <Button
                          type="submit"
                          disabled={!canSubmit || isCreating}
                          className="min-w-[120px]"
                        >
                          {isCreating ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          ) : (
                            <><Plus className="mr-2 h-4 w-4" /> Create App</>
                          )}
                        </Button>
                      )}
                    />
                  </div>
               </form>
            </CardContent>
          </Card>
        )}
      </div>

      <ApplicationSidebar
        open={!!selectedAppName}
        onOpenChange={(open) => !open && setSelectedAppName(null)}
        appName={selectedAppName}
      />
    </main>
  );
}
