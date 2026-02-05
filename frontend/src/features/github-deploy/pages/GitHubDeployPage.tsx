import { useState } from "react";
import { ENV_CONFIG } from "@/shared/config/env";
import {
    Card,
    CardContent,
    CardDescription,
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Github, Clock, Plus, Trash2, ArrowLeft, AlertCircle } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

import { ENVIRONMENTS } from "@/shared/constants/environments";
import {
    createGitOpsMicroserviceStream,
    type GitOpsMicroservicePayload,
    type CronJobPayload,
    type LogEntry,
} from "@/features/gitops/services/gitops-service";
import { ConsoleOutputModal } from "@/components/shared/ConsoleOutputModal";

interface FormErrors {
    environment?: string;
    githubUrl?: string;
}

interface CronJob {
    name: string;
    schedule: string;
    suspend: boolean;
    cmd: string;
}

interface DeploymentConfig {
    environment: string;
    microserviceName: string;
    microserviceUrl: string;
    containerPort: number;
    gitOpsRepoUrl: string;
    gitRepoName: string;
    gitBranch: string;
    argoAppName: string;
    domainName: string;
    envContent: string;
}

export default function GitHubDeployPage() {
    // Step 1 State
    const [selectedEnv, setSelectedEnv] = useState<string>("");
    const [repoPath, setRepoPath] = useState<string>("");
    const [errors, setErrors] = useState<FormErrors>({});

    // Step 2 State
    const [showConfigPanel, setShowConfigPanel] = useState(false);
    const [config, setConfig] = useState<DeploymentConfig>({
        environment: "",
        microserviceName: "",
        microserviceUrl: "",
        containerPort: 3000,
        gitOpsRepoUrl: "",
        gitRepoName: "",
        gitBranch: "",
        argoAppName: "",
        domainName: "",
        envContent: "",
    });
    const [cronJobs, setCronJobs] = useState<CronJob[]>([]);

    // API & Logs State
    const [isLoading, setIsLoading] = useState(false);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [formMessage, setFormMessage] = useState<{
        type: "success" | "error" | "warning";
        message: string;
    } | null>(null);

    const fullUrl = `${ENV_CONFIG.GITHUB_BASE_URL.replace(/\/+$/, "")}/${repoPath}`;

    const validateForm = (): boolean => {
        const newErrors: FormErrors = {};

        if (!selectedEnv) {
            newErrors.environment = "Environment is required";
        }

        if (!repoPath.trim()) {
            newErrors.githubUrl = "Repository path is required";
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleProceed = (e: React.MouseEvent<HTMLButtonElement>) => {
        e.preventDefault();

        if (!validateForm()) {
            return;
        }

        const microserviceName = repoPath; // Assuming repoPath is the name as per instructions
        const gitBranch = selectedEnv;

        setConfig({
            environment: selectedEnv,
            microserviceName: microserviceName,
            microserviceUrl: fullUrl,
            containerPort: 3000,
            gitOpsRepoUrl: `${ENV_CONFIG.GITHUB_BASE_URL.replace(/\/+$/, "")}/git-ops.git`,
            gitRepoName: microserviceName,
            gitBranch: gitBranch,
            argoAppName: `${microserviceName}-${selectedEnv}`,
            domainName: `${microserviceName}-${selectedEnv}.allvestfinance.in`,
            envContent: "",
        });

        setShowConfigPanel(true);
    };

    const handleBack = () => {
        setShowConfigPanel(false);
    };

    const handleSaveConfiguration = async () => {
        setIsLoading(true);
        setLogs([]);
        setFormMessage(null);

        if (!config.envContent.trim()) {
            setFormMessage({
                type: "error",
                message: "Environment Variables field is required.",
            });
            toast.error("Validation Error", {
                description: "Environment Variables field is required.",
            });
            setIsLoading(false);
            return;
        }

        try {
            // Parse environment variables
            const envVars: { name: string; value: string }[] = [];
            if (config.envContent) {
                config.envContent.split("\n").forEach((line) => {
                    const trimmed = line.trim();
                    if (trimmed) {
                        const [name, ...rest] = trimmed.split("=");
                        if (name && rest.length > 0) {
                            envVars.push({ name, value: rest.join("=") });
                        }
                    }
                });
            }

            // Map CronJobs
            const cronJobsPayload: CronJobPayload[] = cronJobs.map(job => ({
                name: job.name,
                schedule: job.schedule,
                suspend: job.suspend,
                cmd: job.cmd.split(",").map(c => c.trim()).filter(Boolean)
            }));

            const payload: GitOpsMicroservicePayload = {
                environment: config.environment,
                microservice_name: config.microserviceName,
                microservice_url: config.microserviceUrl,
                container_port: config.containerPort,
                gitops_repo_url: config.gitOpsRepoUrl,
                git_repo_name: config.gitRepoName,
                git_branch: config.gitBranch,
                argocd_app_name: config.argoAppName,
                domain_name: config.domainName,
                env_content: config.envContent,
                environment_variables: envVars,
                cronjobs: cronJobsPayload.length > 0 ? cronJobsPayload : undefined,
                worker: undefined, // Workers excluded
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
                }
            );
        } catch (error) {
            console.error(error);
            setIsLoading(false);
            const msg = error instanceof Error ? error.message : "An unexpected error occurred";
            setFormMessage({
                type: "error",
                message: msg,
            });
            toast.error("An unexpected error occurred", {
                description: "Please check console for details",
            });
        }
    };

    // CronJob Handlers
    const addCronJob = () => {
        setCronJobs([...cronJobs, { name: "", schedule: "", suspend: false, cmd: "" }]);
    };

    const removeCronJob = (index: number) => {
        setCronJobs(cronJobs.filter((_, i) => i !== index));
    };

    const updateCronJob = (index: number, field: keyof CronJob, value: any) => {
        const newCronJobs = [...cronJobs];
        newCronJobs[index] = { ...newCronJobs[index], [field]: value };
        setCronJobs(newCronJobs);
    };

    if (showConfigPanel) {
        return (
            <div className="p-6 flex flex-col items-center gap-6 w-full">
                <ConsoleOutputModal
                    open={logs.length > 0 || isLoading}
                    logs={logs}
                    isLoading={isLoading}
                    onClose={() => setLogs([])}
                />
                <Card className="w-full max-w-4xl">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Button variant="ghost" size="icon" onClick={handleBack} className="mr-2">
                                <ArrowLeft className="w-4 h-4" />
                            </Button>
                            <div className="p-2 bg-primary/10 rounded-lg">
                                <Github className="w-6 h-6 text-primary" />
                            </div>
                            <div>
                                <CardTitle>Manage GitOps</CardTitle>
                                <CardDescription>
                                    Configure GitOps settings for your microservices.
                                </CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* RO: Environment & Microservice Name */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Environment</Label>
                                <Select value={config.environment} disabled>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {ENVIRONMENTS.map((env) => (
                                            <SelectItem key={env.key} value={env.key}>{env.value}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label>Microservice Name</Label>
                                <Input value={config.microserviceName} disabled />
                            </div>
                        </div>

                        {/* RO: Git Repo URL & Editable: Container Port */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Microservice Git Repo URL</Label>
                                <Input value={config.microserviceUrl} disabled />
                            </div>
                            <div className="space-y-2">
                                <Label>Container Port</Label>
                                <Input
                                    type="number"
                                    value={config.containerPort}
                                    onChange={(e) => setConfig({ ...config, containerPort: Number(e.target.value) })}
                                />
                            </div>
                        </div>

                        {/* RO: GitOps Repo URL & Git Repo Name */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>GitOps Repo URL</Label>
                                <Input value={config.gitOpsRepoUrl} disabled />
                            </div>
                            <div className="space-y-2">
                                <Label>Git Repo Name</Label>
                                <Input value={config.gitRepoName} disabled />
                            </div>
                        </div>

                        {/* RO: Git Branch & Editable: ArgoCD App Name */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Git Branch</Label>
                                <Input value={config.gitBranch} disabled />
                            </div>
                            <div className="space-y-2">
                                <Label>ArgoCD App Name</Label>
                                <Input
                                    value={config.argoAppName}
                                    onChange={(e) => setConfig({ ...config, argoAppName: e.target.value })}
                                />
                            </div>
                        </div>

                        {/* CronJobs Section */}
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
                                    onClick={addCronJob}
                                >
                                    <Plus className="w-4 h-4 mr-2" />
                                    Add CronJob
                                </Button>
                            </div>

                            {cronJobs.length === 0 ? (
                                <div className="text-sm text-muted-foreground text-center py-6 border border-dashed rounded-lg">
                                    No CronJobs configured. Click "Add CronJob" to create one.
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {cronJobs.map((job, index) => (
                                        <Card key={index} className="p-4 relative bg-muted/20">
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="icon"
                                                className="absolute top-2 right-2 text-destructive hover:bg-destructive/10 h-8 w-8"
                                                onClick={() => removeCronJob(index)}
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                            <div className="grid grid-cols-2 gap-4 pr-8">
                                                <div className="space-y-2">
                                                    <Label>Name</Label>
                                                    <Input
                                                        value={job.name}
                                                        onChange={(e) => updateCronJob(index, "name", e.target.value)}
                                                        placeholder="job-name"
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label>Schedule (Cron)</Label>
                                                    <Input
                                                        value={job.schedule}
                                                        onChange={(e) => updateCronJob(index, "schedule", e.target.value)}
                                                        placeholder="0 2 * * *"
                                                    />
                                                </div>
                                                <div className="space-y-2 col-span-2">
                                                    <Label>Command (comma separated)</Label>
                                                    <Input
                                                        value={job.cmd}
                                                        onChange={(e) => updateCronJob(index, "cmd", e.target.value)}
                                                        placeholder="npm, run, sync"
                                                    />
                                                </div>
                                                <div className="flex items-center space-x-2 pt-2">
                                                    <Switch
                                                        checked={job.suspend}
                                                        onCheckedChange={(checked) => updateCronJob(index, "suspend", checked)}
                                                    />
                                                    <Label>Suspend</Label>
                                                </div>
                                            </div>
                                        </Card>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Workers - Removed as per requirements */}

                        {/* Editable: Domain Name */}
                        <div className="pt-4 border-t space-y-2">
                            <Label>Domain Name</Label>
                            <Input
                                value={config.domainName}
                                onChange={(e) => setConfig({ ...config, domainName: e.target.value })}
                            />
                        </div>

                        {/* Editable: Environment Variables */}
                        <div className="space-y-2">
                            <Label>Environment Variables (.env) <span className="text-destructive">*</span></Label>
                            <Textarea
                                value={config.envContent}
                                onChange={(e) => setConfig({ ...config, envContent: e.target.value })}
                                placeholder="DB_HOST=localhost"
                                className="font-mono min-h-[150px]"
                            />
                            <p className="text-xs text-muted-foreground">
                                Format: KEY=VALUE (one per line)
                            </p>
                        </div>

                        <Button onClick={handleSaveConfiguration} className="w-full">
                            Save Configuration
                        </Button>

                        {formMessage && (
                            <Alert
                                variant="default"
                                className={`mt-4 ${formMessage.type === "success"
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
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="p-6 flex flex-col items-center gap-6 w-full">
            <Card className="w-full max-w-2xl">
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <div className="p-2 bg-primary/10 rounded-lg">
                            <Github className="w-6 h-6 text-primary" />
                        </div>
                        <div>
                            <CardTitle>GitHub Deployment</CardTitle>
                            <CardDescription>
                                Configure your GitHub repository for deployment.
                            </CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <form className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Column 1: Environment */}
                            <div className="space-y-2">
                                <Label
                                    htmlFor="environment"
                                    className={errors.environment ? "text-destructive" : ""}
                                >
                                    Environment
                                </Label>
                                <Select
                                    value={selectedEnv}
                                    onValueChange={(val) => {
                                        setSelectedEnv(val);
                                        if (errors.environment) {
                                            setErrors((prev) => ({
                                                ...prev,
                                                environment: undefined,
                                            }));
                                        }
                                    }}
                                >
                                    <SelectTrigger
                                        id="environment"
                                        className={
                                            errors.environment
                                                ? "border-destructive focus:ring-destructive"
                                                : ""
                                        }
                                    >
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
                                {errors.environment && (
                                    <p className="text-sm text-destructive">
                                        {errors.environment}
                                    </p>
                                )}
                            </div>

                            {/* Column 2: GitHub URL */}
                            <div className="space-y-2">
                                <Label
                                    htmlFor="githubUrl"
                                    className={errors.githubUrl ? "text-destructive" : ""}
                                >
                                    GitHub Repository URL
                                </Label>

                                <Input
                                    id="githubUrl"
                                    type="text"
                                    // Combine base URL + repo path
                                    value={`${ENV_CONFIG.GITHUB_BASE_URL.replace(/\/+$/, "")}/${repoPath}`}
                                    onChange={(e) => {
                                        // Extract only the repo path part (everything after the base URL)
                                        const fullValue = e.target.value;
                                        const basePath = ENV_CONFIG.GITHUB_BASE_URL.replace(/\/+$/, "");

                                        // Remove base URL prefix to get just the repo path
                                        let newPath = fullValue;
                                        if (fullValue.startsWith(`${basePath}/`)) {
                                            newPath = fullValue.substring(basePath.length + 1);
                                        } else if (fullValue.startsWith(basePath)) {
                                            newPath = fullValue.substring(basePath.length);
                                        }

                                        setRepoPath(newPath);

                                        if (errors.githubUrl) {
                                            setErrors((prev) => ({
                                                ...prev,
                                                githubUrl: undefined,
                                            }));
                                        }
                                    }}
                                    placeholder={`${ENV_CONFIG.GITHUB_BASE_URL.replace(/\/+$/, "")}/repo-name`}
                                    className={
                                        errors.githubUrl
                                            ? "border-destructive focus-visible:ring-destructive"
                                            : ""
                                    }
                                />

                                {errors.githubUrl && (
                                    <p className="text-sm text-destructive">{errors.githubUrl}</p>
                                )}
                            </div>
                        </div>

                        <Button
                            type="button"
                            onClick={handleProceed}
                            className="w-full"
                            disabled={!selectedEnv || !repoPath.trim()}
                        >
                            Proceed
                        </Button>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}
