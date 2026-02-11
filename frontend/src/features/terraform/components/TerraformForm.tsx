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

interface TerraformConfig {
    client: string;
    environment: string;
    resourceType: string;
    bucketName: string;
    isPublic: boolean;
}

export function TerraformForm() {
    const [config, setConfig] = useState<TerraformConfig>({
        client: "",
        environment: "",
        resourceType: "",
        bucketName: "",
        isPublic: false,
    });

    const [formMessage, setFormMessage] = useState<{
        type: "success" | "error";
        message: string;
    } | null>(null);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setFormMessage(null);

        // Basic validation
        if (!config.client || !config.environment || !config.resourceType) {
            setFormMessage({
                type: "error",
                message: "Please fill in all required fields",
            });
            return;
        }

        if (config.resourceType === "s3_bucket" && !config.bucketName) {
            setFormMessage({
                type: "error",
                message: "Bucket name is required",
            });
            return;
        }

        console.log("Submitting Terraform config:", config);

        setFormMessage({
            type: "success",
            message: "Terraform configuration submitted successfully",
        });
        toast.success("Configuration Submitted", {
            description: "Your Terraform resource request has been processed.",
        });
    };

    const handleCancel = () => {
        setConfig({
            client: "",
            environment: "",
            resourceType: "",
            bucketName: "",
            isPublic: false,
        });
        setFormMessage(null);
    };

    return (
        <Card className="w-full max-w-2xl">
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
                                onValueChange={(val) => setConfig({ ...config, client: val })}
                            >
                                <SelectTrigger id="client">
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
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="environment">Environment</Label>
                            <Select
                                value={config.environment}
                                onValueChange={(val) => setConfig({ ...config, environment: val })}
                            >
                                <SelectTrigger id="environment">
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
                                }}
                            >
                                <SelectTrigger id="resourceType">
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
                        </div>
                    </div>

                    {config.resourceType === "s3_bucket" && (
                        <div className="p-4 border rounded-lg bg-muted/20 space-y-4 animate-in fade-in slide-in-from-top-2">
                            <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">
                                Bucket Configuration
                            </h3>

                            <div className="space-y-2">
                                <Label htmlFor="bucketName">Bucket Name</Label>
                                <Input
                                    id="bucketName"
                                    value={config.bucketName}
                                    onChange={(e) => setConfig({ ...config, bucketName: e.target.value })}
                                    placeholder="e.g. my-app-assets"
                                />
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
                        <Button type="submit">Submit Configuration</Button>
                    </div>
                </form>
            </CardContent>
        </Card>
    );
}
