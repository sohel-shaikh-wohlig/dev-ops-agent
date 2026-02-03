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
import { AlertCircle, FileCode, Search, Download, Plus, ArrowLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";
// @ts-ignore
import jsPDF from "jspdf";
// @ts-ignore
import autoTable from "jspdf-autotable";

import {
  updateConfigMap,
  fetchConfigMapValues,
} from "./services/configmap-service";
import { ApiError } from "@/services/api-client";

export function ConfigMapPage() {
  const [viewMode, setViewMode] = useState<'search' | 'edit'>('search');
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

  // Search State
  const [searchParams, setSearchParams] = useState({
    environment: "dev",
    microserviceName: "",
  });
  const [configValues, setConfigValues] = useState<Record<string, string> | null>(null);

  // Edit State
  // Result State
  const [updateResult, setUpdateResult] = useState<any | null>(null);

  const form = useForm({
    defaultValues: {
      environment: "dev",
      microserviceName: "",
      repoUrl: "https://github.com/allvest-wm/git-ops.git",
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
            if (line.trim() && !/^[A-Za-z_0-9]+=[^\n]+$/.test(line)) {
              return `Invalid format at line: "${line}". Expected KEY=VALUE (mixed case allowed)`;
            }
          }
        }
        return undefined;
      },
    },
    onSubmit: async ({ value }) => {
      // Handle Dry-Run Update
      await handleDryRunUpdate(value);
    },
  });

  const handleFetchValues = async () => {
    if (!searchParams.microserviceName) {
      toast.error("Validation Error", { description: "Microservice Name is required" });
      return;
    }
    setIsLoading(true);
    setApiError(null);
    setConfigValues(null);
    try {
      const data = await fetchConfigMapValues(searchParams.microserviceName, searchParams.environment);
      const config = data.config || {};

      if (Object.keys(config).length === 0) {
        toast.info("No Configuration Found", { description: "The returned configuration is empty." });
      } else {
        toast.success("Configuration Fetched", { description: `Found ${Object.keys(config).length} keys.` });
      }
      setConfigValues(config);
    } catch (error) {
      if (error instanceof ApiError) {
        setApiError(error.data);
      } else {
        toast.error("Fetch Failed", { description: "Could not fetch configuration values." });
      }
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadPdf = () => {
    if (!configValues) return;

    try {
      const doc = new jsPDF();

      doc.setFontSize(16);
      doc.text("ConfigMap Values", 14, 20);

      doc.setFontSize(12);
      doc.text(`Microservice: ${searchParams.microserviceName}`, 14, 30);
      doc.text(`Environment: ${searchParams.environment}`, 14, 36);

      const tableData = Object.entries(configValues).map(([key, value]) => [key, value]);

      autoTable(doc, {
        startY: 45,
        head: [['Key', 'Value']],
        body: tableData,
        theme: 'striped',
        headStyles: { fillColor: [66, 66, 66] }
      });

      doc.save(`configmap-${searchParams.microserviceName}-${searchParams.environment}.pdf`);
      toast.success("PDF Downloaded");
    } catch (error) {
      console.error("PDF generation failed:", error);
      toast.error("Download Failed", { description: "Could not generate PDF." });
    }
  };

  const handleCommit = async () => {
    if (!updateResult || !updateResult.changes) return;

    setIsLoading(true);
    setApiError(null);

    // Filter only new/updated keys to prevent unnecessary processing/noise
    // We rely on values.yaml changes or data.env changes as the source of truth for values
    const changedKeys = new Set(
      updateResult.changes
        .filter((c: any) => (c.file === 'values.yaml' || c.file === 'data.env') && (c.type === 'ADD' || c.type === 'UPDATE'))
        .map((c: any) => c.key)
    );

    if (changedKeys.size === 0) {
      toast.info("No Changes to Commit", { description: "All values are unchanged." });
      setIsLoading(false);
      return;
    }

    // specific filtering: retrieve values from the form state to ensure consistency,
    // but only for keys that are marked as changed
    // specific filtering: retrieve values from the form state to ensure consistency,
    // but only for keys that are marked as changed
    const formValues = form.state.values;

    // Double check we aren't missing anything from the change detection (e.g. if regex failed)
    // Alternatively, we could reconstruct from change.new_value, but keeping original formatting/comments (if any, though we stripped them) is nice.
    // actually, reconstructing from changes is safer as it matches exactly what backend saw as "new"

    // Better reconstruction approach:
    const filteredEnvContent = updateResult.changes
      .filter((c: any) => (c.file === 'values.yaml' || c.file === 'data.env') && (c.type === 'ADD' || c.type === 'UPDATE'))
      .map((c: any) => `${c.key}=${c.new_value}`)
      .join('\n');

    try {
      const payload = {
        environment_name: formValues.environment,
        microservice_name: formValues.microserviceName,
        gitops_url: formValues.repoUrl,
        argocd_app_name: formValues.argoAppName,
        env_content: filteredEnvContent, // Send ONLY changed values
        auto_commit: true,
        auto_sync_argocd: formValues.autoSync,
        git_branch: formValues.gitBranch,
      };

      const data = await updateConfigMap(payload);

      toast.success("Configuration Committed", {
        description: `Committed: ${data.git_committed ? "Yes" : "No"}, Synced: ${data.argocd_synced ? "Yes" : "No"}`,
      });

      // Reset
      setUpdateResult(null);
      form.reset();
      // Optionally switch back to search or clear
      setViewMode('search');
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.data && error.data.detail) {
          setApiError(error.data);
          return;
        }
        toast.error("Commit failed", { description: error.message });
      } else {
        toast.error("Commit failed", {
          description: "Could not apply configuration changes.",
        });
      }
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDryRunUpdate = async (value: typeof form.state.values) => {
    setIsLoading(true);
    setApiError(null);
    setUpdateResult(null);
    try {
      const payload = {
        environment_name: value.environment,
        microservice_name: value.microserviceName,
        gitops_url: value.repoUrl,
        argocd_app_name: value.argoAppName,
        env_content: value.envContent,
        auto_commit: false, // Ensure no commit is triggered
        auto_sync_argocd: false, // Cannot sync without commit
        git_branch: value.gitBranch,
      };

      const data = await updateConfigMap(payload);
      setUpdateResult(data);
      toast.success("Dry-Run Complete", { description: "Review changes below." });
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.data && error.data.detail) {
          setApiError(error.data);
          return;
        }
        toast.error("Operation failed", { description: error.message });
      } else {
        if (!apiError) {
          toast.error("Operation failed", {
            description: "Could not generate configuration preview.",
          });
        }
      }
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 flex justify-center w-full">
      <Card className="w-full max-w-4xl">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-primary/10 rounded-lg">
                <FileCode className="w-6 h-6 text-primary" />
              </div>
              <div>
                <CardTitle>
                  {updateResult ? "Review Changes" : "Manage ConfigMap"}
                </CardTitle>
                <CardDescription>
                  {viewMode === 'search'
                    ? "View and download existing configuration values."
                    : updateResult
                      ? "Review proposed changes before committing."
                      : "Preview configuration updates (Dry-Run)."}
                </CardDescription>
              </div>
            </div>
            <div>
              {viewMode === 'search' ? (
                <Button onClick={() => setViewMode('edit')}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add / Update
                </Button>
              ) : (
                <Button variant="outline" onClick={() => {
                  setViewMode('search');
                  setUpdateResult(null);
                  form.reset();
                }}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Search
                </Button>
              )}
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
                  Array.isArray(apiError.detail) ? (
                    <ul className="list-disc list-inside space-y-1 mt-2">
                      {apiError.detail.map((err, index) => (
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

          {viewMode === 'search' ? (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Environment</Label>
                  <Select
                    value={searchParams.environment}
                    onValueChange={(val) => setSearchParams(prev => ({ ...prev, environment: val }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select environment" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="dev">Dev</SelectItem>
                      <SelectItem value="uat">Stage</SelectItem>
                      <SelectItem value="prod">Prod</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Microservice Name</Label>
                  <Input
                    value={searchParams.microserviceName}
                    onChange={(e) => setSearchParams(prev => ({ ...prev, microserviceName: e.target.value }))}
                    placeholder="e.g. user-service"
                  />
                </div>
                <div className="flex items-end">
                  <Button onClick={handleFetchValues} disabled={isLoading} className="w-full">
                    {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4 mr-2" />}
                    Fetch Values
                  </Button>
                </div>
              </div>

              {configValues && (
                <div className="space-y-4 pt-4 border-t animate-in fade-in slide-in-from-bottom-5">
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold">ConfigMap Values</h3>
                    <Button variant="secondary" onClick={handleDownloadPdf}>
                      <Download className="w-4 h-4 mr-2" />
                      Download PDF
                    </Button>
                  </div>

                  <div className="border rounded-md overflow-hidden">
                    <div className="max-h-[500px] overflow-y-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-muted bg-opacity-50 sticky top-0">
                          <tr className="border-b">
                            <th className="text-left p-3 font-medium w-1/3">Key</th>
                            <th className="text-left p-3 font-medium">Value</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {Object.entries(configValues).length > 0 ? (
                            Object.entries(configValues).map(([key, value]) => (
                              <tr key={key} className="hover:bg-muted/30">
                                <td className="p-3 font-mono text-xs">{key}</td>
                                <td className="p-3 font-mono text-xs break-all">{value}</td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan={2} className="p-8 text-center text-muted-foreground">
                                No configuration values found.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              {!updateResult ? (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    form.handleSubmit();
                  }}
                  className="space-y-6 animate-in fade-in slide-in-from-left-5"
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
                              <SelectItem value="dev">Dev</SelectItem>
                              <SelectItem value="uat">Stage</SelectItem>
                              <SelectItem value="prod">Prod</SelectItem>
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

                  <div className="grid grid-cols-2 gap-4">
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
                  </div>

                  {/* Auto Sync removed from UI as it requires auto_commit which is false */}
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
                            "Generate Update Preview"
                          )}
                        </Button>
                      )}
                    />
                  </CardFooter>
                </form>
              ) : null}

              {/* Result Table */}
              {updateResult && updateResult.changes && (
                <div className="space-y-4 pt-4 border-t animate-in fade-in slide-in-from-bottom-5">
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold">Update Preview (Dry Run)</h3>
                  </div>

                  <div className="border rounded-md overflow-hidden">
                    <div className="max-h-[500px] overflow-y-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-muted bg-opacity-50 sticky top-0">
                          <tr className="border-b">
                            <th className="text-left p-3 font-medium">Key</th>
                            <th className="text-left p-3 font-medium">Value</th>
                            <th className="text-left p-3 font-medium w-24">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {/* Sort: ADD/UPDATE first, then UNCHANGED */
                            [...updateResult.changes]
                              .sort((a: any, b: any) => {
                                const getScore = (type: string) => type === 'ADD' ? 0 : type === 'UPDATE' ? 1 : 2;
                                return getScore(a.type) - getScore(b.type);
                              })
                              .map((change: any, i: number) => (
                                <tr key={i} className="hover:bg-muted/30">
                                  <td className="p-3 font-mono text-xs">{change.key}</td>
                                  <td className="p-3 font-mono text-xs break-all">{change.new_value}</td>
                                  <td className="p-3 text-xs font-semibold">
                                    <span className={`px-2 py-1 rounded-full ${change.type === 'ADD' ? 'bg-green-100 text-green-800' :
                                      change.type === 'UPDATE' ? 'bg-yellow-100 text-yellow-800' :
                                        'bg-gray-100 text-gray-600'
                                      }`}>
                                      {change.type === 'ADD' ? 'NEW' : change.type}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <Alert className="bg-blue-50 text-blue-800 border-blue-200">
                    <AlertCircle className="w-4 h-4 text-blue-800" />
                    <AlertTitle>Preview Only</AlertTitle>
                    <AlertDescription>
                      This is a dry-run. No changes have been committed to the repository.
                    </AlertDescription>
                  </Alert>
                  <div className="flex justify-end gap-3 mt-4">
                    <Button
                      variant="outline"
                      onClick={() => setUpdateResult(null)}
                      disabled={isLoading}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleCommit}
                      disabled={isLoading}
                      className="bg-green-600 hover:bg-green-700 text-white"
                    >
                      {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      Commit Changes
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Removed DialogPrimitive.Root preview modal */}
    </div>
  );
}
