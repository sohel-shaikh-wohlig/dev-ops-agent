import React from "react";
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
import { AlertCircle, FileCode } from "lucide-react";

// Assuming Tabs component exists in ui, otherwise I will use a simple state switch for tabs.
// I will verify standard shadcn structure.

export function ConfigMapPage() {
  const form = useForm({
    defaultValues: {
      environment: "Dev",
      microserviceName: "",
      repoUrl: "",
      argoAppName: "",
      autoSync: false,
      envContent: "",
    },
    validators: {
      onSubmit: ({ value }) => {
        if (!value.microserviceName) return "Microservice Name is required";
        if (!value.repoUrl) return "GitOps Repo URL is required";

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
      console.log("Submitted ConfigMap:", value);
      // Here we would call the API
    },
  });

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
                        <SelectItem value="Dev">Dev</SelectItem>
                        <SelectItem value="Stage">Stage</SelectItem>
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
                children={([canSubmit, isSubmitting]) => (
                  <Button
                    type="submit"
                    disabled={!canSubmit}
                    className="w-full"
                  >
                    {isSubmitting ? "Submitting..." : "Create ConfigMap"}
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
