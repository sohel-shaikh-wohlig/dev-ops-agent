
import { apiClient } from "@/services/api-client";

export interface ConfigMapPayload {
    environment_name: string;
    microservice_name: string;
    gitops_url: string;
    argocd_app_name: string;
    env_content: string;
    auto_commit: boolean;
    auto_sync_argocd: boolean;
    git_branch: string;
}

export interface Change {
    file: string;
    type: string;
    key?: string;
    old_value?: string;
    new_value?: string;
}

export interface Summary {
    total_changes: number;
    values_yaml_changes: number;
    configmap_yaml_changes: number;
    additions: number;
    updates: number;
}

export interface PreviewResponse {
    session_id: string;
    changes: Change[];
    summary: Summary;
    env_variables?: Record<string, string>;
}

export interface UpdateResponse {
    git_committed: boolean;
    argocd_synced: boolean;
    status: string;
    changes: Change[];
}

export const previewConfigMap = async (payload: ConfigMapPayload): Promise<PreviewResponse> => {
    return apiClient.post<PreviewResponse>('/configmap/preview', payload);
};

export const updateConfigMap = async (payload: ConfigMapPayload): Promise<UpdateResponse> => {
    return apiClient.post<UpdateResponse>('/configmap/update', payload);
};

export interface ConfigValuesResponse {
    status: string;
    microservice: string;
    environment: string;
    config: Record<string, string>;
}

export const fetchConfigMapValues = async (microserviceName: string, env: string): Promise<ConfigValuesResponse> => {
    const queryParams = new URLSearchParams({
        microservice_name: microserviceName,
        env: env
    }).toString();
    return apiClient.get<ConfigValuesResponse>(`/gitops/config-values?${queryParams}`);
};
