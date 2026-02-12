export interface TerraformProvisionPayload {
    client_name: string;
    environment: string;
    terraform_repo_url: string;
    resource_type: string;
    resource_config: Record<string, any>;
}

export const provisionTerraform = async (payload: TerraformProvisionPayload) => {
    const response = await fetch("http://127.0.0.1:8000/api/terraform/provision", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to provision Terraform resources");
    }

    return response.json();
};
