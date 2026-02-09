import { useState, useRef, useEffect } from "react";
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
import { AlertCircle, GitGraph, Loader2, Clock, Plus, Trash2, Briefcase } from "lucide-react";
import { toast } from "sonner";
import { Switch } from "@/components/ui/switch";
import { ConsoleOutputModal } from "@/components/shared/ConsoleOutputModal";
import {
  createGitOpsMicroserviceStream,
  type GitOpsMicroservicePayload,
  type CronJobPayload,
  type WorkerPayload,
  type LogEntry,
} from "./services/gitops-service";


import { ENVIRONMENTS } from "@/shared/constants/environments";

export function GitOpsPage() {
  console.log("GitOpsPage mounting");
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

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const [manuallyEdited, setManuallyEdited] = useState<{
    gitRepoName: boolean;
    argoAppName: boolean;
    domainName: boolean;
    microserviceUrl: boolean;
  }>({
    gitRepoName: false,
    argoAppName: false,
    domainName: false,
    microserviceUrl: false,
  });

  const [formMessage, setFormMessage] = useState<{
    type: "success" | "error" | "warning";
    message: string;
  } | null>(null);

  const form = useForm({
    defaultValues: {
      environment: "dev", // Default to dev as per requirements maybe? Or kept empty? "Automatically set... to dev" when env=dev.
      microserviceName: "",
      microserviceUrl: "",
      containerPort: 3000,
      repoUrl: "https://github.com/allvest-wm/git-ops.git",
      gitRepoName: "",
      gitBranch: "dev", // Defaulting to match environment
      argoAppName: "",
      domainName: "",
      envContent: "",
      // CronJobs Array
      cronJobs: [] as {
        name: string;
        schedule: string;
        suspend: boolean;
        cmd: string;
      }[],
      // Workers Array
      // Worker Configuration (Single)
      enableWorker: false,
      worker: {
        name: "language-translation",
        workerType: "languageTranslation",
        secrets: "vertex_ai, bq",
        additionalEnv: ""
      }
    },
    validators: {
      onSubmit: ({ value }) => {
        // Required Fields
        if (!value.environment) return "Environment is required";
        if (!value.microserviceName) return "Microservice Name is required";
        if (!value.microserviceUrl) return "Microservice URL is required";
        if (!value.repoUrl) return "GitOps Repo URL is required";
        if (!value.gitRepoName) return "Git Repo Name is required";
        if (!value.gitBranch) return "Git Branch is required";
        if (!value.argoAppName) return "ArgoCD App Name is required";
        if (!value.domainName) return "Domain Name is required";

        // Dynamic Validation: Branch must match Environment for specific cases
        if (value.environment === "dev" && value.gitBranch !== "dev") {
          return "For 'dev' environment, Git Branch must be 'dev'";
        }
        if (value.environment === "uat" && value.gitBranch !== "uat") {
          return "For 'uat' environment, Git Branch must be 'uat'";
        }

        try {
          if (
            !value.repoUrl.startsWith("http") &&
            !value.repoUrl.startsWith("git@") &&
            !value.repoUrl.startsWith("ssh://")
          ) {
            return "GitOps Repo URL must be a valid URL (http, ssh, etc.)";
          }
        } catch (_) {
          return "GitOps Repo URL must be a valid URL";
        }

        // Port Validation
        if (isNaN(Number(value.containerPort))) {
          return "Container Port must be a number";
        }

        if (!value.envContent) {
          return "Please provide .env content";
        }

        if (value.envContent) {
          const lines = value.envContent.split("\n");
          for (const line of lines) {
            if (line.trim() && !/^[A-Z_0-9]+=[^\n]+$/.test(line)) {
              return `Invalid format at line: "${line}". Expected KEY=VALUE`;
            }
          }
        }

        // CronJob Validation
        if (value.cronJobs && value.cronJobs.length > 0) {
          for (const job of value.cronJobs) {
            if (!job.name) return "CronJob Name is required";
            if (!job.schedule) return "Cron Schedule is required";
            // Basic cron validation
            if (job.schedule.trim().split(" ").length < 5) {
              return `Invalid Cron Schedule for ${job.name || 'job'}`;
            }
            if (!job.cmd) return "Cron Command is required";
          }
        }

        // Worker Validation (Only if enabled)
        if (value.enableWorker) {
          if (!value.worker.name) return "Worker Name is required";
          if (!value.worker.workerType) return "Worker Type is required";
          if (!value.worker.secrets) return "At least one secret is required";

          if (value.worker.additionalEnv) {
            const lines = value.worker.additionalEnv.split("\n");
            for (const line of lines) {
              if (line.trim() && !/^[A-Z_0-9]+=[^\n]+$/.test(line)) {
                return `Worker Env: Invalid format at "${line}". Expected KEY=VALUE`;
              }
            }
          }
        }

        return undefined;
      },
    },
    onSubmit: async ({ value }) => {
      setIsLoading(true);
      setApiError(null);
      setLogs([]); // Clear previous logs
      setFormMessage(null);
      try {
        // Parse environment variables
        const envVars: { name: string; value: string }[] = [];
        if (value.envContent) {
          value.envContent.split("\n").forEach((line) => {
            const trimmed = line.trim();
            if (trimmed) {
              const [name, ...rest] = trimmed.split("=");
              envVars.push({ name, value: rest.join("=") });
            }
          });
        }

        let cronJobsPayload: CronJobPayload[] | undefined = undefined;
        if (value.cronJobs && value.cronJobs.length > 0) {
          cronJobsPayload = value.cronJobs.map(job => ({
            name: job.name,
            schedule: job.schedule,
            suspend: job.suspend,
            cmd: job.cmd.split(",").map(c => c.trim()).filter(Boolean)
          }));
        }

        let workerPayload: WorkerPayload | undefined = undefined;
        if (value.enableWorker) {
          const additionalEnvRecord: Record<string, string> = {};
          if (value.worker.additionalEnv) {
            value.worker.additionalEnv.split("\n").forEach((line) => {
              const trimmed = line.trim();
              if (trimmed) {
                const [name, ...rest] = trimmed.split("=");
                additionalEnvRecord[name] = rest.join("=");
              }
            });
          }

          workerPayload = {
            name: value.worker.name,
            workerType: value.worker.workerType,
            secrets: value.worker.secrets.split(",").map(s => s.trim()).filter(Boolean),
            additionalEnv: Object.keys(additionalEnvRecord).length > 0 ? additionalEnvRecord : undefined
          };
        }

        const payload: GitOpsMicroservicePayload = {
          environment: value.environment,
          microservice_name: value.microserviceName,
          microservice_url: value.microserviceUrl,
          container_port: Number(value.containerPort),
          gitops_repo_url: value.repoUrl,
          git_repo_name: value.gitRepoName,
          git_branch: value.gitBranch,
          argocd_app_name: value.argoAppName,
          domain_name: value.domainName,
          env_content: value.envContent,
          environment_variables: envVars,
          cronjobs: cronJobsPayload,
          worker: workerPayload
        };

        await createGitOpsMicroserviceStream(
          payload,
          (log) => {
            setLogs((prev) => [...prev, log]);
          },
          () => {
            setFormMessage({
              type: "success",
              message: "Your configuration has been successfully applied.",
            });
            toast.success("GitOps Configuration Saved", {
              description: "Your configuration has been successfully applied.",
            });
            setIsLoading(false);
            form.reset();
            setManuallyEdited({
              gitRepoName: false,
              argoAppName: false,
              domainName: false,
              microserviceUrl: false,
            });
          },
          (errorMessage) => {
            setFormMessage({
              type: "error",
              message: errorMessage,
            });
            setIsLoading(false);
            toast.error("Submission Failed", {
              description: errorMessage,
            });
            // Try to set API error if it looks like one
            if (errorMessage.includes("API Error")) {
              setApiError({ status: "Error", message: errorMessage });
            }
          }
        );

      } catch (error) {
        console.error(error);
        setIsLoading(false);
        const msg = error instanceof Error ? error.message : "An unexpected error occurred";
        setFormMessage({ type: "error", message: msg });
        toast.error("An unexpected error occurred", {
          description: "Please check console for details",
        });
      }
    },
  });

  return (
    <div className="p-6 flex flex-col items-center gap-6 w-full">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-primary/10 rounded-lg">
              <GitGraph className="w-6 h-6 text-primary" />
            </div>
            <div>
              <CardTitle>Manage GitOps</CardTitle>
              <CardDescription>
                Configure GitOps settings for your microservices.
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
                {Array.isArray(apiError.detail) ? (
                  <ul className="list-disc list-inside space-y-1 mt-2">
                    {apiError.detail.map((err, index) => (
                      <li key={index}>
                        <span className="font-semibold">
                          {err.loc && err.loc[1] ? `${err.loc[1]}: ` : ""}
                        </span>
                        {err.msg}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>
                    {typeof apiError.detail === "string"
                      ? apiError.detail
                      : apiError.message || "Something went wrong."}
                  </p>
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
                      onValueChange={(val) => {
                        field.handleChange(val);
                        // Dynamic Logic
                        if (val === "dev") {
                          form.setFieldValue("gitBranch", "dev");
                        } else if (val === "uat") {
                          form.setFieldValue("gitBranch", "uat");
                        }

                        // Auto-population logic
                        const msName = form.getFieldValue("microserviceName");
                        if (msName) {
                          if (!manuallyEdited.argoAppName) {
                            form.setFieldValue(
                              "argoAppName",
                              `${msName}-${val}`,
                            );
                          }
                          if (!manuallyEdited.domainName) {
                            form.setFieldValue(
                              "domainName",
                              `${msName}-${val}.allvestfinance.in`,
                            );
                          }
                        }
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select environment" />
                      </SelectTrigger>
                      <SelectContent>
                        {ENVIRONMENTS.map((env) => (
                          <SelectItem key={env.key} value={env.key}>
                            {env.value}
                          </SelectItem>
                        ))}
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
                      onChange={(e) => {
                        const val = e.target.value;
                        field.handleChange(val);

                        // Auto-population logic
                        const env = form.getFieldValue("environment");

                        if (!manuallyEdited.gitRepoName) {
                          form.setFieldValue("gitRepoName", val);
                        }

                        if (!manuallyEdited.argoAppName) {
                          form.setFieldValue(
                            "argoAppName",
                            val && env ? `${val}-${env}` : "",
                          );
                        }

                        if (!manuallyEdited.domainName) {
                          form.setFieldValue(
                            "domainName",
                            val && env ? `${val}-${env}.allvestfinance.in` : "",
                          );
                        }

                        if (!manuallyEdited.microserviceUrl) {
                          form.setFieldValue(
                            "microserviceUrl",
                            val ? `https://github.com/allvest-wm/${val}` : "",
                          );
                        }
                      }}
                      placeholder="e.g. user-service"
                    />
                  </div>
                )}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <form.Field
                name="microserviceUrl"
                validators={{
                  onBlur: ({ value }) => {
                    const gitUrlPattern =
                      /^https:\/\/[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\/.*$/;
                    if (!value) return "Microservice URL is required";
                    if (!gitUrlPattern.test(value)) {
                      return "Please enter a valid Git repository URL (e.g. https://github.com/allvest-wm/)";
                    }
                    return undefined;
                  },
                }}
                children={(field) => (
                  <div className="space-y-2">
                    <Label
                      htmlFor={field.name}
                      className={
                        field.state.meta.errors.length ? "text-destructive" : ""
                      }
                    >
                      Microservice Git Repo URL
                    </Label>
                    <Input
                      id={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => {
                        field.handleChange(e.target.value);
                        setManuallyEdited((prev) => ({
                          ...prev,
                          microserviceUrl: true,
                        }));
                      }}
                      placeholder="https://github.com/allvest-wm/"
                      className={
                        field.state.meta.errors.length
                          ? "border-destructive focus-visible:ring-destructive"
                          : ""
                      }
                    />
                    {field.state.meta.errors.length ? (
                      <p className="text-sm text-destructive">
                        {field.state.meta.errors.join(", ")}
                      </p>
                    ) : null}
                  </div>
                )}
              />

              <form.Field
                name="containerPort"
                children={(field) => (
                  <div className="space-y-2">
                    <Label htmlFor={field.name}>Container Port</Label>
                    <Input
                      id={field.name}
                      type="number"
                      value={field.state.value}
                      onChange={(e) =>
                        field.handleChange(Number(e.target.value))
                      }
                      placeholder="3000"
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
                      onChange={(e) => {
                        field.handleChange(e.target.value);
                        setManuallyEdited((prev) => ({
                          ...prev,
                          gitRepoName: true,
                        }));
                      }}
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
                      onChange={(e) => {
                        field.handleChange(e.target.value);
                        setManuallyEdited((prev) => ({
                          ...prev,
                          argoAppName: true,
                        }));
                      }}
                      placeholder="e.g. user-service-dev"
                    />
                  </div>
                )}
              />
            </div>

            <div className="space-y-4 pt-4 border-t">
              <div className="flex items-center justify-between">
                <Label className="text-base flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  CronJobs
                </Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => form.pushFieldValue("cronJobs", { name: "", schedule: "", suspend: false, cmd: "" })}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add CronJob
                </Button>
              </div>

              <form.Field
                name="cronJobs"
                mode="array"
                children={(field) => (
                  <div className="space-y-4">
                    {field.state.value.map((_, i) => (
                      <Card key={i} className="p-4 relative bg-muted/20">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="absolute top-2 right-2 text-destructive hover:bg-destructive/10 h-8 w-8"
                          onClick={() => field.removeValue(i)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                        <div className="grid grid-cols-2 gap-4 pr-8">
                          <form.Field
                            name={`cronJobs[${i}].name`}
                            children={(subField) => (
                              <div className="space-y-2">
                                <Label>Name</Label>
                                <Input
                                  value={subField.state.value}
                                  onChange={(e) => subField.handleChange(e.target.value)}
                                  placeholder="job-name"
                                />
                              </div>
                            )}
                          />
                          <form.Field
                            name={`cronJobs[${i}].schedule`}
                            children={(subField) => (
                              <div className="space-y-2">
                                <Label>Schedule (Cron)</Label>
                                <Input
                                  value={subField.state.value}
                                  onChange={(e) => subField.handleChange(e.target.value)}
                                  placeholder="0 2 * * *"
                                />
                              </div>
                            )}
                          />
                          <form.Field
                            name={`cronJobs[${i}].cmd`}
                            children={(subField) => (
                              <div className="space-y-2 col-span-2">
                                <Label>Command (comma separated)</Label>
                                <Input
                                  value={subField.state.value}
                                  onChange={(e) => subField.handleChange(e.target.value)}
                                  placeholder="npm, run, sync"
                                />
                              </div>
                            )}
                          />
                          <form.Field
                            name={`cronJobs[${i}].suspend`}
                            children={(subField) => (
                              <div className="flex items-center space-x-2 pt-2">
                                <Switch
                                  checked={subField.state.value}
                                  onCheckedChange={subField.handleChange}
                                />
                                <Label>Suspend</Label>
                              </div>
                            )}
                          />
                        </div>
                      </Card>
                    ))}
                    {field.state.value.length === 0 && (
                      <div className="text-sm text-muted-foreground text-center py-6 border border-dashed rounded-lg">
                        No CronJobs configured. Click "Add CronJob" to create one.
                      </div>
                    )}
                  </div>
                )}
              />
            </div>

            <div className="space-y-4 pt-4 border-t">
              <div className="flex items-center justify-between">
                <Label className="text-base flex items-center gap-2">
                  <Briefcase className="w-4 h-4" />
                  Workers
                </Label>
              </div>

              <div className="space-y-4 pt-4 border-t">
                <div className="flex items-center justify-between">
                  <Label className="text-base flex items-center gap-2">
                    <Briefcase className="w-4 h-4" />
                    Worker Configuration
                  </Label>
                  <form.Field
                    name="enableWorker"
                    children={(field) => (
                      <div className="flex items-center space-x-2">
                        <Switch
                          checked={field.state.value}
                          onCheckedChange={field.handleChange}
                        />
                        <Label>Enable Worker</Label>
                      </div>
                    )}
                  />
                </div>

                <form.Field
                  name="enableWorker"
                  children={(field) => (
                    <>
                      {field.state.value && (
                        <Card className="p-4 bg-muted/20">
                          <div className="grid grid-cols-2 gap-4">
                            <form.Field
                              name="worker.name"
                              children={(subField) => (
                                <div className="space-y-2">
                                  <Label>Worker Name</Label>
                                  <Input
                                    value={subField.state.value}
                                    onChange={(e) => subField.handleChange(e.target.value)}
                                    placeholder="language-translation"
                                  />
                                </div>
                              )}
                            />
                            <form.Field
                              name="worker.workerType"
                              children={(subField) => (
                                <div className="space-y-2">
                                  <Label>Worker Type</Label>
                                  <Input
                                    value={subField.state.value}
                                    onChange={(e) => subField.handleChange(e.target.value)}
                                    placeholder="languageTranslation"
                                  />
                                </div>
                              )}
                            />
                            <form.Field
                              name="worker.secrets"
                              children={(subField) => (
                                <div className="space-y-2 col-span-2">
                                  <Label>Secrets (comma separated)</Label>
                                  <Input
                                    value={subField.state.value}
                                    onChange={(e) => subField.handleChange(e.target.value)}
                                    placeholder="vertex_ai, bq"
                                  />
                                  <p className="text-xs text-muted-foreground">
                                    Supported: vertex_ai, bq
                                  </p>
                                </div>
                              )}
                            />
                            <form.Field
                              name="worker.additionalEnv"
                              children={(subField) => (
                                <div className="space-y-2 col-span-2">
                                  <Label>Additional Environment Variables</Label>
                                  <Textarea
                                    value={subField.state.value}
                                    onChange={(e) => subField.handleChange(e.target.value)}
                                    placeholder="BATCH_SIZE=100"
                                    className="font-mono min-h-[100px]"
                                  />
                                  <p className="text-xs text-muted-foreground">
                                    Format: KEY=VALUE (one per line)
                                  </p>
                                </div>
                              )}
                            />
                          </div>
                        </Card>
                      )}
                    </>
                  )}
                />
              </div>
            </div>

            <form.Field
              name="domainName"
              children={(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Domain Name</Label>
                  <Input
                    id={field.name}
                    value={field.state.value}
                    onChange={(e) => {
                      field.handleChange(e.target.value);
                      setManuallyEdited((prev) => ({
                        ...prev,
                        domainName: true,
                      }));
                    }}
                    placeholder="e.g. api.example.com"
                  />
                </div>
              )}
            />

            <div className="space-y-4 pt-4 border-t">
              <Label className="text-base">Environment Variables (.env)</Label>

              <form.Field
                name="envContent"
                children={(field) => (
                  <div className="space-y-2">
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

            <CardFooter className="px-0 pt-4 flex-col gap-4">
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
                      "Save Configuration"
                    )}
                  </Button>
                )}
              />
              {formMessage && (
                <Alert
                  variant="default"
                  className={`w-full ${formMessage.type === "success"
                      ? "border-green-900/50 text-green-600 dark:text-green-400 bg-green-900/10 [&>svg]:text-green-600 dark:[&>svg]:text-green-400"
                      : formMessage.type === "warning"
                        ? "border-yellow-900/50 text-yellow-600 dark:text-yellow-400 bg-yellow-900/10 [&>svg]:text-yellow-600 dark:[&>svg]:text-yellow-400"
                        : "border-red-900/50 text-red-600 dark:text-red-400 bg-red-900/10 [&>svg]:text-red-600 dark:[&>svg]:text-red-400"
                    }`}
                >
                  {formMessage.type === "success" ? (
                    <div className="h-4 w-4 mr-2 rounded-full bg-green-500" />
                  ) : formMessage.type === "warning" ? (
                    <div className="h-4 w-4 mr-2 rounded-full bg-yellow-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4" />
                  )}
                  <AlertTitle>
                    {formMessage.type === "success"
                      ? "Success"
                      : formMessage.type === "warning"
                        ? "Warning"
                        : "Error"}
                  </AlertTitle>
                  <AlertDescription>{formMessage.message}</AlertDescription>
                </Alert>
              )}
            </CardFooter>
          </form>
        </CardContent>
      </Card>

      {/* Console Output Modal */}
      <ConsoleOutputModal
        open={logs.length > 0 || isLoading}
        logs={logs}
        isLoading={isLoading}
        onClose={() => setLogs([])}
      />
    </div>
  );
}
