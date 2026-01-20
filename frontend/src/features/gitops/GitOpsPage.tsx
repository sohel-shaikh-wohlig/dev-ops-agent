
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
import { AlertCircle, GitGraph, Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
    createGitOpsMicroservice,
    type GitOpsMicroservicePayload,
} from "./services/gitops-service";
import { ApiError } from "@/services/api-client";

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
                    if (!value.repoUrl.startsWith("http") && !value.repoUrl.startsWith("git@") && !value.repoUrl.startsWith("ssh://")) {
                        return "GitOps Repo URL must be a valid URL (http, ssh, etc.)";
                    }
                } catch (_) {
                    return "GitOps Repo URL must be a valid URL";
                }

                // Port Validation
                if (isNaN(Number(value.containerPort))) {
                    return "Container Port must be a number";
                }

                // Domain Validation
                // if (!/^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$/.test(value.domainName) && value.domainName !== 'localhost') {
                //     return "Domain Name must be a valid domain";
                // }

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

                return undefined;
            },
        },
        onSubmit: async ({ value }) => {
            setIsLoading(true);
            setApiError(null);
            try {
                // Parse environment variables
                const envVars: { name: string; value: string }[] = [];
                if (value.envContent) {
                    value.envContent.split("\n").forEach(line => {
                        const trimmed = line.trim();
                        if (trimmed) {
                            const [name, ...rest] = trimmed.split("=");
                            envVars.push({ name, value: rest.join("=") });
                        }
                    });
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
                    environment_variables: envVars
                };

                await createGitOpsMicroservice(payload);

                toast.success("GitOps Configuration Saved", {
                    description: "Your configuration has been successfully applied."
                });
                form.reset();
                setManuallyEdited({
                    gitRepoName: false,
                    argoAppName: false,
                    domainName: false,
                    microserviceUrl: false,
                });
            } catch (error) {
                console.error(error);
                if (error instanceof ApiError) {
                    if (error.data && error.data.detail) {
                        setApiError(error.data);
                    } else {
                        toast.error("Submission Failed", {
                            description: error.message
                        });
                    }
                } else {
                    toast.error("Submission Failed", {
                        description: "Could not save configuration."
                    });
                }
            } finally {
                setIsLoading(false);
            }
        },
    });

    return (
        <div className="p-6 flex justify-center w-full">
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
                                                <span className="font-semibold">{err.loc && err.loc[1] ? `${err.loc[1]}: ` : ""}</span>
                                                {err.msg}
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <p>{typeof apiError.detail === 'string' ? apiError.detail : (apiError.message || "Something went wrong.")}</p>
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
                                                        form.setFieldValue("argoAppName", `${msName}-${val}`);
                                                    }
                                                    if (!manuallyEdited.domainName) {
                                                        form.setFieldValue("domainName", `${msName}-${val}.allvestfinance.in`);
                                                    }
                                                }
                                            }}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select environment" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="dev">Dev</SelectItem>
                                                <SelectItem value="uat">UAT</SelectItem>
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
                                            onChange={(e) => {
                                                const val = e.target.value;
                                                field.handleChange(val);

                                                // Auto-population logic
                                                const env = form.getFieldValue("environment");

                                                if (!manuallyEdited.gitRepoName) {
                                                    form.setFieldValue("gitRepoName", val);
                                                }

                                                if (!manuallyEdited.argoAppName) {
                                                    form.setFieldValue("argoAppName", val && env ? `${val}-${env}` : "");
                                                }

                                                if (!manuallyEdited.domainName) {
                                                    form.setFieldValue("domainName", val && env ? `${val}-${env}.allvestfinance.in` : "");
                                                }

                                                if (!manuallyEdited.microserviceUrl) {
                                                    form.setFieldValue("microserviceUrl", val ? `https://github.com/allvest-wm/${val}.git` : "");
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
                                        const gitUrlPattern = /^https:\/\/[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\/.*\.git$/;
                                        if (!value) return "Microservice URL is required";
                                        if (!gitUrlPattern.test(value)) {
                                            return "Please enter a valid Git repository URL (e.g. https://github.com/org/repo.git)";
                                        }
                                        return undefined;
                                    }
                                }}
                                children={(field) => (
                                    <div className="space-y-2">
                                        <Label htmlFor={field.name} className={field.state.meta.errors.length ? "text-destructive" : ""}>
                                            Microservice Git Repo URL
                                        </Label>
                                        <Input
                                            id={field.name}
                                            value={field.state.value}
                                            onBlur={field.handleBlur}
                                            onChange={(e) => {
                                                field.handleChange(e.target.value);
                                                setManuallyEdited((prev) => ({ ...prev, microserviceUrl: true }));
                                            }}
                                            placeholder="https://github.com/allvest-wm/service.git"
                                            className={field.state.meta.errors.length ? "border-destructive focus-visible:ring-destructive" : ""}
                                        />
                                        {field.state.meta.errors.length ? (
                                            <p className="text-sm text-destructive">{field.state.meta.errors.join(", ")}</p>
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
                                            onChange={(e) => field.handleChange(Number(e.target.value))}
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
                                                setManuallyEdited((prev) => ({ ...prev, gitRepoName: true }));
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
                                                setManuallyEdited((prev) => ({ ...prev, argoAppName: true }));
                                            }}
                                            placeholder="e.g. user-service-dev"
                                        />
                                    </div>
                                )}
                            />
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
                                            setManuallyEdited((prev) => ({ ...prev, domainName: true }));
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
                                            "Save Configuration"
                                        )}
                                    </Button>
                                )}
                            />
                        </CardFooter>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}
