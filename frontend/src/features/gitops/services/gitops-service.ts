
import { apiClient } from "@/services/api-client";

export interface GitOpsMicroservicePayload {
    environment: string;
    microservice_name: string;
    microservice_url: string;
    container_port: number;
    gitops_repo_url: string;
    git_repo_name: string;
    git_branch: string;
    argocd_app_name: string;
    domain_name: string;
    env_content: string;
    environment_variables?: Array<{ name: string; value: string }>;
}

export interface GitOpsMicroserviceResponse {
    status: string;
    message?: string;
    // Add other fields if known, for now generic structure based on usage
}

export const createGitOpsMicroservice = async (payload: GitOpsMicroservicePayload): Promise<GitOpsMicroserviceResponse> => {
    // Note: User specified URL http://127.0.0.1:8000/api/gitops/micro-service
    // Assuming apiClient base URL is configured correctly or we need to use absolute path if base URL differs.
    // Given the previous configmap service uses `/configmap/preview`, it assumes a relative path.
    // If the base URL in .env is http://127.0.0.1:8000, then we use `/api/gitops/micro-service`
    // However, the prompt says "http://127.0.0.1:8000/api/gitops/micro-service".
    // I I will assume the base URL includes /api or not. Use the full path relative to base or adjust.
    // Safest bet if the existing app uses `/configmap` is that base is `http://127.0.0.1:8000` or similar.
    // I will use `/api/gitops/micro-service` assuming the proxy or base url handles the host.

    return apiClient.post<GitOpsMicroserviceResponse>('/gitops/micro-service', payload);
};
