import { useState } from "react";
import { useForm } from "@tanstack/react-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Switch } from "@/components/ui/switch";
import { AlertCircle, FileCode, Loader2 } from "lucide-react";
import { toast } from "sonner";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import {
  previewConfigMap,
  updateConfigMap,
  type PreviewResponse,
} from "./services/configmap-service";
import { ApiError } from "@/services/api-client";

export function ConfigMapPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<{
    status: string;
    message: string;
    detail?: {
      loc: string[];
      msg: string;
      type: string;
    }[];
  } | null>(null);

  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);

  const form = useForm({
    defaultValues: {
      environment: "development",
      microserviceName: "",
      repoUrl: "",
      gitRepoName: "",
      argoAppName: "",
      autoSync: false,
      envContent: "",
      gitBranch: "dev",
    },
    validators: {
      onSubmit: ({ value }) => {
        if (!value.microserviceName) return "Microservice Name is required";
        if (!value.repoUrl) return "GitOps Repo URL is required";
        if (!value.gitRepoName) return "Git Repo Name is required";
        if (!value.gitBranch) return "Git Branch is required";

        if (!value.envContent) {
          return "Please provide .env content";
        }

        // Regex validation for content
        if (value.envContent) {
          const lines = value.envContent.split("\n");
          for (const line of lines) {
            if (line.trim() && !/^[A-Z_0-9]+=[^\n]+$/.test(line)) {
              return `Invalid format at line: "${line}". Expected KEY=VALUE`;
            }
          }
        }
        return undefined;
      },
    },
    onSubmit: async ({ value }) => {
      // Handle Preview
      await handlePreview(value);
    },
  });

  const handlePreview = async (value: typeof form.state.values) => {
    setIsLoading(true);
    setApiError(null);
    try {
      const payload = {
        environment_name: value.environment,
        microservice_name: value.microserviceName,
        gitops_url: value.repoUrl,
        argocd_app_name: value.argoAppName,
        env_content: value.envContent,
        auto_commit: true,
        auto_sync_argocd: value.autoSync,
        git_branch: value.gitBranch,
      };

      const data = await previewConfigMap(payload);
      setPreviewData(data);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.data && error.data.detail) {
          setApiError(error.data);
          return;
        }
        // Fallback to error message
        toast.error("Preview failed", { description: error.message });
      } else {
        // Only show toast if it wasn't a handled API error
        if (!apiError) {
          toast.error("Preview failed", {
            description: "Could not generate configuration preview.",
          });
        }
      }
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdate = async () => {
    if (!previewData) return;
    setIsLoading(true);
    setApiError(null);
    const value = form.state.values;

    try {
      const payload = {
        environment_name: value.environment,
        microservice_name: value.microserviceName,
        gitops_url: value.repoUrl,
        argocd_app_name: value.argoAppName,
        env_content: value.envContent,
        auto_commit: true,
        auto_sync_argocd: value.autoSync,
        git_branch: value.gitBranch,
      };

      const data = await updateConfigMap(payload);

      toast.success("Configuration Updated", {
        description: `Committed: ${data.git_committed ? "Yes" : "No"}, Synced: ${data.argocd_synced ? "Yes" : "No"}`,
      });

      // Reset
      setPreviewData(null);
      form.reset();
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.data && error.data.detail) {
          setApiError(error.data);
          return;
        }
        toast.error("Update failed", { description: error.message });
      } else {
        toast.error("Update failed", {
          description: "Could not apply configuration changes.",
        });
      }
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 flex justify-center w-full">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-primary/10 rounded-lg">
              <FileCode className="w-6 h-6 text-primary" />
            </div>
            <div>
              <CardTitle>Manage ConfigMap</CardTitle>
              <CardDescription>
                Create or update configuration for your microservices.
              </CardDescription>
            </div>
          </div>
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
                  <ul className="list-disc list-inside space-y-1 mt-2">
                    {apiError.detail.map((err, index) => (
                      <li key={index}>
                        <span className="font-semibold">{err.loc[1]}:</span>{" "}
                        {err.msg}
                      </li>
                    ))}
                  </ul>
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
                name="environment"
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
                        <SelectItem value="development">Dev</SelectItem>
                        <SelectItem value="staging">Stage</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              />

              <form.Field
                name="microserviceName"
                children={(field) => (
                  <div className="space-y-2">
                    <Label htmlFor={field.name}>Microservice Name</Label>
                    <Input
                      id={field.name}
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      placeholder="e.g. user-service"
                    />
                  </div>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <form.Field
                name="repoUrl"
                children={(field) => (
                  <div className="space-y-2">
                    <Label htmlFor={field.name}>GitOps Repo URL</Label>
                    <Input
                      id={field.name}
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      placeholder="https://github.com/org/repo.git"
                    />
                  </div>
                )}
              />

              <form.Field
                name="gitRepoName"
                children={(field) => (
                  <div className="space-y-2">
                    <Label htmlFor={field.name}>Git Repo Name</Label>
                    <Input
                      id={field.name}
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      placeholder="e.g. repo-name"
                    />
                  </div>
                )}
              />
            </div>

            <form.Field
              name="gitBranch"
              children={(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Git Branch</Label>
                  <Input
                    id={field.name}
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    placeholder="e.g. main"
                  />
                </div>
              )}
            />

            <form.Field
              name="argoAppName"
              children={(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>ArgoCD App Name</Label>
                  <Input
                    id={field.name}
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    placeholder="e.g. user-service-dev"
                  />
                </div>
              )}
            />

            <form.Field
              name="autoSync"
              children={(field) => (
                <div className="flex items-center space-x-2 py-2">
                  <Switch
                    id={field.name}
                    checked={field.state.value}
                    onCheckedChange={field.handleChange}
                  />
                  <Label htmlFor={field.name}>Auto Sync ArgoCD</Label>
                </div>
              )}
            />

            <div className="space-y-4 pt-4 border-t">
              <Label className="text-base">Environment Variables (.env)</Label>

              <form.Field
                name="envContent"
                children={(field) => (
                  <div className="space-y-2 animate-in fade-in zoom-in-95 duration-200">
                    <Textarea
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      placeholder="DB_HOST=localhost&#10;DB_PORT=5432"
                      className="font-mono min-h-[150px]"
                    />
                    <p className="text-xs text-muted-foreground">
                      Format: KEY=VALUE (one per line)
                    </p>
                  </div>
                )}
              />
            </div>

            {/* Form Level Errors */}
            <form.Subscribe
              selector={(state) => state.errors}
              children={(errors) =>
                errors.length > 0 ? (
                  <Alert variant="destructive">
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

            <CardFooter className="px-0 pt-4">
              <form.Subscribe
                selector={(state) => [state.canSubmit, state.isSubmitting]}
                children={([canSubmit]) => (
                  <Button
                    type="submit"
                    disabled={!canSubmit || isLoading}
                    className="w-full"
                  >
                    {isLoading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      "Preview Changes"
                    )}
                  </Button>
                )}
              />
            </CardFooter>
          </form>
        </CardContent>
      </Card>

      {/* Preview Modal (Simple Overlay for now, or use DialogPrimitive if styled) */}
      {previewData && (
        <DialogPrimitive.Root open={!!previewData}>
          <DialogPrimitive.Portal>
            <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/80" />
            <DialogPrimitive.Content className="fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 sm:rounded-lg max-h-[90vh] overflow-y-auto">
              <div className="flex flex-col space-y-1.5 text-center sm:text-left">
                <DialogPrimitive.Title className="text-lg font-semibold leading-none tracking-tight">
                  Preview Changes
                </DialogPrimitive.Title>
                <DialogPrimitive.Description className="text-sm text-muted-foreground">
                  Review the pending configuration changes.
                </DialogPrimitive.Description>
              </div>
              <div className="py-4">
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="bg-muted p-2 rounded">
                      <span className="font-semibold">Total Changes:</span> {previewData.summary.total_changes}
                    </div>
                    <div className="bg-muted p-2 rounded">
                      <span className="font-semibold">Updates:</span> {previewData.summary.updates}
                    </div>
                    <div className="bg-muted p-2 rounded">
                      <span className="font-semibold">Additions:</span> {previewData.summary.additions}
                    </div>
                    <div className="bg-muted p-2 rounded">
                      <span className="font-semibold">ConfigMap Changes:</span> {previewData.summary.configmap_yaml_changes}
                    </div>
                  </div>

                  {previewData.changes && previewData.changes.length > 0 && (
                    <div className="border rounded-md max-h-[300px] overflow-auto">
                      <div className="p-2 bg-muted border-b font-semibold text-sm">Detailed Changes</div>
                      <div className="divide-y">
                        {previewData.changes.map((change, i) => (
                          <div key={i} className="p-3 text-sm">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-bold text-primary">{change.key}</span>
                              <span className={`text-xs px-2 py-0.5 rounded-full ${change.type === 'UPDATE' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'}`}>
                                {change.type}
                              </span>
                            </div>
                            <div className="text-xs text-muted-foreground mb-1">File: {change.file}</div>
                            {change.old_value && (
                              <div className="grid grid-cols-[60px_1fr] gap-2 text-xs">
                                <span className="text-red-500">Old:</span>
                                <span className="font-mono break-all">{change.old_value}</span>
                              </div>
                            )}
                            <div className="grid grid-cols-[60px_1fr] gap-2 text-xs">
                              <span className="text-green-500">New:</span>
                              <span className="font-mono break-all">{change.new_value}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex justify-end space-x-2">
                <Button
                  variant="outline"
                  onClick={() => setPreviewData(null)}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <Button onClick={handleUpdate} disabled={isLoading}>
                  {isLoading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    "Proceed & Update"
                  )}
                </Button>
              </div>
            </DialogPrimitive.Content>
          </DialogPrimitive.Portal>
        </DialogPrimitive.Root>
      )}
    </div>
  );
}
