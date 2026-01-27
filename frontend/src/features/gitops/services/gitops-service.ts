
import { apiClient } from "@/services/api-client";

export interface CronJobPayload {
    name: string;
    schedule: string;
    suspend: boolean;
    cmd: string[];
}

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
    cronjobs?: CronJobPayload[];
}

export interface GitOpsMicroserviceResponse {
    status: string;
    message?: string;
    // Add other fields if known, for now generic structure based on usage
}

// Basic create function (retained for backward compatibility if needed, but updated to use stream potentially or kept as is)
export const createGitOpsMicroservice = async (payload: GitOpsMicroservicePayload): Promise<GitOpsMicroserviceResponse> => {
    // This old method expects a JSON response, but the backend now streams. 
    // We should either update this to wait for the final result or deprecate it.
    // For now, let's implement the streaming version which is the goal.
    return apiClient.post<GitOpsMicroserviceResponse>('/gitops/micro-service', payload);
};

export interface LogEntry {
    type: 'log' | 'result' | 'error';
    level?: string;
    message?: string;
    timestamp?: number;
    data?: any;
}

export const createGitOpsMicroserviceStream = async (
    payload: GitOpsMicroservicePayload,
    onLog: (entry: LogEntry) => void,
    onComplete: (data: GitOpsMicroserviceResponse) => void,
    onError: (error: string) => void
) => {
    try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/gitops/micro-service`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            let errorMessage = response.statusText;
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorData.message || errorMessage;
            } catch (e) {
                // Ignore json parse error
            }
            throw new Error(`API Error: ${errorMessage}`);
        }

        if (!response.body) {
            throw new Error('ReadableStream not supported in this browser.');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep the last partial line in buffer

            for (const line of lines) {
                if (line.trim()) {
                    try {
                        const entry = JSON.parse(line) as LogEntry;
                        if (entry.type === 'result') {
                            onComplete(entry.data as GitOpsMicroserviceResponse);
                        } else if (entry.type === 'error') {
                            onError(entry.message || 'Unknown error');
                        } else {
                            onLog(entry);
                        }
                    } catch (e) {
                        console.error("Failed to parse stream line", line, e);
                    }
                }
            }
        }
    } catch (error: any) {
        onError(error.message || 'Network error');
    }
};
