"""
Kubernetes context mappings
Maps environments to kubectl contexts
"""

CLUSTER_CONTEXTS = {
    "dev": "dev",
    "development": "dev",
    "test": "test",
    "staging": "staging",
    "stage": "staging",
    "production": "production",
    "prod": "production",
    "qa": "qa",
    "uat": "uat"
}

def get_cluster_context(environment: str) -> str:
    """Get kubectl context for environment"""
    return CLUSTER_CONTEXTS.get(environment.lower(), "dev")