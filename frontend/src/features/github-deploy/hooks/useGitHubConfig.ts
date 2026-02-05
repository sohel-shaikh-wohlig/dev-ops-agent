import { ENV_CONFIG } from '@/shared/config/env';

export const useGitHubConfig = () => {
    return {
        baseUrl: ENV_CONFIG.GITHUB_BASE_URL
    };
};
