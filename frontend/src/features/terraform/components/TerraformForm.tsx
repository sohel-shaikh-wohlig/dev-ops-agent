import { useState } from "react";
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
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Cloud, AlertCircle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

import { ENVIRONMENTS } from "@/shared/constants/environments";
import { CLIENTS, RESOURCE_TYPES } from "@/shared/constants/terraform";
import { provisionTerraform } from "../services/terraform-service";
import { WebSocketResponseView } from "./WebSocketResponseView";

interface TerraformConfig {
    client: string;
    environment: string;
    terraformRepoUrl: string;
    resourceType: string;
    bucketName: string;
    isPublic: boolean;
}

export function TerraformForm() {
    const [config, setConfig] = useState<TerraformConfig>({
        client: "",
        environment: "",
        terraformRepoUrl: "",
        resourceType: "",
        bucketName: "",
        isPublic: false,
    });

    const [isLoading, setIsLoading] = useState(false);
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [formMessage, setFormMessage] = useState<{
        type: "success" | "error";
        message: string;
    } | null>(null);

    const [showResponseScreen, setShowResponseScreen] = useState<{ prNumber: number; repoName: string; branchName: string } | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setFormMessage(null);
        const newErrors: Record<string, string> = {};

        // Validation
        if (!config.client) {
            newErrors.client = "Client is required";
        }

        if (!config.environment) {
            newErrors.environment = "Environment is required";
        }

        if (!config.resourceType) {
            newErrors.resourceType = "Resource type is required";
        }

        if (!config.terraformRepoUrl) {
            newErrors.terraformRepoUrl = "Terraform Git Repo URL is required";
        } else if (!/^https:\/\/|^git@github\.com/.test(config.terraformRepoUrl)) {
            newErrors.terraformRepoUrl = "Enter a valid Git repository URL (https:// or git@github.com)";
        }

        if (config.resourceType === "gcs" && !config.bucketName) {
            newErrors.bucketName = "Bucket name is required";
        }

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        // Clear errors if valid
        // Clear errors if valid
        setErrors({});
        setIsLoading(true);

        try {
            const payload = {
                client_name: config.client,
                environment: config.environment,
                terraform_repo_url: config.terraformRepoUrl,
                resource_type: config.resourceType,
                resource_config: config.resourceType === "gcs" ? {
                    bucket_name: config.bucketName,
                    is_public: config.isPublic,
                } : {},
            };

            const response = await provisionTerraform(payload);

            if (response.status === "success" && response.pr_url) {
                const prUrl = response.pr_url;
                const prNumber = prUrl.split("/").pop();

                if (prNumber && !isNaN(Number(prNumber))) {
                    // Extract owner and repo from PR URL (e.g., https://github.com/owner/repo/pull/34)
                    const urlParts = prUrl.split("/"); // ["https:", "", "github.com", "owner", "repo", "pull", "34"]
                    const repoIndex = urlParts.indexOf("pull") - 1;
                    const ownerIndex = repoIndex - 1;

                    if (repoIndex > 0 && ownerIndex > 0) {
                        const repoName = `${urlParts[ownerIndex]}/${urlParts[repoIndex]}`;
                        setShowResponseScreen({ prNumber: Number(prNumber), repoName, branchName: response.branch || "" });
                    }
                }
            }

            setFormMessage({
                type: "success",
                message: "Terraform configuration submitted successfully",
            });
            toast.success("Configuration Submitted", {
                description: "Your Terraform resource request has been processed.",
            });

        } catch (error: any) {
            console.error(error);
            setFormMessage({
                type: "error",
                message: error.message || "An error occurred during provisioning",
            });
            toast.error("Submission Failed", {
                description: error.message || "An error occurred during provisioning",
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleCancel = () => {
        setConfig({
            client: "",
            environment: "",
            terraformRepoUrl: "",
            resourceType: "",
            bucketName: "",
            isPublic: false,
        });
        setFormMessage(null);
        setErrors({});
    };

    return showResponseScreen ? (
        <WebSocketResponseView prNumber={showResponseScreen.prNumber} repoName={showResponseScreen.repoName} branchName={showResponseScreen.branchName} />
    ) : (
        <Card className="w-full max-w-x1">
            <CardHeader>
                <div className="flex items-center gap-2">
                    <div className="p-2 bg-primary/10 rounded-lg">
                        <Cloud className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                        <CardTitle>Terraform Resources</CardTitle>
                        <CardDescription>
                            Provision and manage infrastructure using Terraform.
                        </CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="client">Client</Label>
                            <Select
                                value={config.client}
                                onValueChange={(val) => {
                                    setConfig({ ...config, client: val });
                                    if (errors.client) setErrors({ ...errors, client: "" });
                                }}
                            >
                                <SelectTrigger id="client" className={errors.client ? "border-destructive" : ""}>
                                    <SelectValue placeholder="Select client" />
                                </SelectTrigger>
                                <SelectContent>
                                    {CLIENTS.map((client) => (
                                        <SelectItem key={client.key} value={client.key}>
                                            {client.value}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {errors.client && (
                                <p className="text-sm text-destructive">{errors.client}</p>
                            )}
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="environment">Environment</Label>
                            <Select
                                value={config.environment}
                                onValueChange={(val) => {
                                    setConfig({ ...config, environment: val });
                                    if (errors.environment) setErrors({ ...errors, environment: "" });
                                }}
                            >
                                <SelectTrigger id="environment" className={errors.environment ? "border-destructive" : ""}>
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
                                <p className="text-sm text-destructive">{errors.environment}</p>
                            )}
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="resourceType">Resource Type</Label>
                            <Select
                                value={config.resourceType}
                                onValueChange={(val) => {
                                    setConfig({
                                        ...config,
                                        resourceType: val,
                                        bucketName: "",
                                        isPublic: false,
                                    });
                                    setFormMessage(null);
                                    if (errors.resourceType) {
                                        const newErrors: Record<string, string> = { ...errors, resourceType: "" };
                                        delete newErrors.bucketName; // Clear bucket error if switching type
                                        setErrors(newErrors);
                                    }
                                }}
                            >
                                <SelectTrigger id="resourceType" className={errors.resourceType ? "border-destructive" : ""}>
                                    <SelectValue placeholder="Select resource type" />
                                </SelectTrigger>
                                <SelectContent>
                                    {RESOURCE_TYPES.map((type) => (
                                        <SelectItem key={type.key} value={type.key}>
                                            {type.value}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {errors.resourceType && (
                                <p className="text-sm text-destructive">{errors.resourceType}</p>
                            )}
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="terraformRepoUrl">Terraform Git Repo URL</Label>
                            <Input
                                id="terraformRepoUrl"
                                value={config.terraformRepoUrl}
                                onChange={(e) => {
                                    setConfig({ ...config, terraformRepoUrl: e.target.value });
                                    if (errors.terraformRepoUrl) setErrors({ ...errors, terraformRepoUrl: "" });
                                }}
                                placeholder="https://github.com/org/repo.git or git@github.com:org/repo.git"
                                className={errors.terraformRepoUrl ? "border-destructive" : ""}
                            />
                            {errors.terraformRepoUrl && (
                                <p className="text-sm text-destructive">{errors.terraformRepoUrl}</p>
                            )}
                        </div>
                    </div>

                    {config.resourceType === "gcs" && (
                        <div className="p-4 border rounded-lg bg-muted/20 space-y-4 animate-in fade-in slide-in-from-top-2">
                            <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">
                                Bucket Configuration
                            </h3>

                            <div className="space-y-2">
                                <Label htmlFor="bucketName">Bucket Name</Label>
                                <Input
                                    id="bucketName"
                                    value={config.bucketName}
                                    onChange={(e) => {
                                        setConfig({ ...config, bucketName: e.target.value });
                                        if (errors.bucketName) setErrors({ ...errors, bucketName: "" });
                                    }}
                                    placeholder="e.g. my-app-assets"
                                    className={errors.bucketName ? "border-destructive" : ""}
                                />
                                {errors.bucketName && (
                                    <p className="text-sm text-destructive">{errors.bucketName}</p>
                                )}
                            </div>

                            <div className="flex items-center justify-between p-3 border rounded-md bg-background">
                                <div className="space-y-0.5">
                                    <Label htmlFor="public-access">Public Access</Label>
                                    <p className="text-sm text-muted-foreground">
                                        Allow public read access to objects in this bucket
                                    </p>
                                </div>
                                <Switch
                                    id="public-access"
                                    checked={config.isPublic}
                                    onCheckedChange={(checked) => setConfig({ ...config, isPublic: checked })}
                                />
                            </div>
                        </div>
                    )}

                    {formMessage && (
                        <Alert
                            variant={formMessage.type === "success" ? "default" : "destructive"}
                            className={
                                formMessage.type === "success"
                                    ? "border-green-500/50 text-green-600 dark:text-green-400 bg-green-500/10 [&>svg]:text-green-600"
                                    : ""
                            }
                        >
                            {formMessage.type === "success" ? (
                                <CheckCircle2 className="h-4 w-4" />
                            ) : (
                                <AlertCircle className="h-4 w-4" />
                            )}
                            <AlertTitle>
                                {formMessage.type === "success" ? "Success" : "Error"}
                            </AlertTitle>
                            <AlertDescription>{formMessage.message}</AlertDescription>
                        </Alert>
                    )}

                    <div className="flex justify-end gap-3 pt-4 border-t">
                        <Button type="button" variant="outline" onClick={handleCancel}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isLoading}>
                            {isLoading ? "Submitting..." : "Submit Configuration"}
                        </Button>
                    </div>
                </form>
            </CardContent>
        </Card>
    );
}
