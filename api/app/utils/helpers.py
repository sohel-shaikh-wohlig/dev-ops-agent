from typing import Dict, Any, List, Optional
from datetime import datetime
import re

def build_application_spec(
    name: str,
    project: str,
    repo_url: str,
    path: str = ".",
    target_revision: str = "HEAD",
    destination_server: str = "https://kubernetes.default.svc",
    destination_namespace: str = "default",
    auto_sync: bool = False,
    auto_prune: bool = False,
    self_heal: bool = False,
    auto_create_namespace: bool = True,
    revision_history_limit: int = 10,
    chart: Optional[str] = None,
    helm_values: Optional[Dict] = None,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Build ArgoCD application specification
    
    Args:
        name: Application name
        project: ArgoCD project name
        repo_url: Git repository URL
        path: Path to the application within the repository
        target_revision: Git revision to sync to (branch, tag, or commit SHA)
        destination_server: Kubernetes cluster server URL
        destination_namespace: Target namespace for deployment
        auto_sync: Enable automatic sync
        auto_prune: Enable automatic pruning of resources
        self_heal: Enable self-healing
        auto_create_namespace: Automatically create namespace if it doesn't exist
        revision_history_limit: Number of revisions to keep for rollback
        chart: Helm chart name (for Helm applications)
        helm_values: Helm values (for Helm applications)
        labels: Metadata labels
        annotations: Metadata annotations
        
    Returns:
        Complete ArgoCD application specification
    """
    
    # Base spec
    spec = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Application",
        "metadata": {
            "name": name,
            "namespace": "argocd"  # ArgoCD namespace
        },
        "spec": {
            "project": project,
            "source": {
                "repoURL": repo_url,
                "targetRevision": target_revision
            },
            "destination": {
                "server": destination_server,
                "namespace": destination_namespace
            },
            "revisionHistoryLimit": revision_history_limit
        }
    }
    
    # Add labels if provided
    if labels:
        spec["metadata"]["labels"] = labels
    
    # Add annotations if provided
    if annotations:
        spec["metadata"]["annotations"] = annotations
    
    # Configure source based on type
    if chart:
        # Helm chart
        spec["spec"]["source"]["chart"] = chart
        if helm_values:
            spec["spec"]["source"]["helm"] = {
                "values": helm_values
            }
    else:
        # Git path
        spec["spec"]["source"]["path"] = path
    
    # Configure sync policy
    sync_policy = {}
    
    # Add syncOptions for auto-create namespace
    if auto_create_namespace:
        sync_policy["syncOptions"] = ["CreateNamespace=true"]
    
    # Auto sync configuration
    if auto_sync:
        sync_policy["automated"] = {
            "prune": auto_prune,
            "selfHeal": self_heal
        }
    
    # Only add syncPolicy if it has content
    if sync_policy:
        spec["spec"]["syncPolicy"] = sync_policy
    
    return spec


def build_project_spec(
    name: str,
    description: Optional[str] = None,
    source_repos: Optional[List[str]] = None,
    destinations: Optional[List[Dict[str, str]]] = None,
    cluster_resource_whitelist: Optional[List[Dict[str, str]]] = None,
    namespace_resource_blacklist: Optional[List[Dict[str, str]]] = None,
    roles: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Build ArgoCD project specification"""
    
    spec: Dict[str, Any] = {
        "metadata": {
            "name": name
        },
        "spec": {}
    }
    
    if description:
        spec["spec"]["description"] = description
    
    if source_repos:
        spec["spec"]["sourceRepos"] = source_repos
    
    if destinations:
        spec["spec"]["destinations"] = destinations
    
    if cluster_resource_whitelist:
        spec["spec"]["clusterResourceWhitelist"] = cluster_resource_whitelist
    
    if namespace_resource_blacklist:
        spec["spec"]["namespaceResourceBlacklist"] = namespace_resource_blacklist
    
    if roles:
        spec["spec"]["roles"] = roles
    
    return spec


def build_repository_spec(
    repo_url: str,
    repo_type: str = "git",
    name: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    ssh_private_key: Optional[str] = None,
    insecure: bool = False,
    tls_client_cert_data: Optional[str] = None,
    tls_client_cert_key: Optional[str] = None,
    enable_oci: bool = False
) -> Dict[str, Any]:
    """Build repository specification"""
    
    spec: Dict[str, Any] = {
        "repo": repo_url,
        "type": repo_type
    }
    
    if name:
        spec["name"] = name
    
    if username:
        spec["username"] = username
    
    if password:
        spec["password"] = password
    
    if ssh_private_key:
        spec["sshPrivateKey"] = ssh_private_key
    
    if insecure:
        spec["insecure"] = insecure
    
    if tls_client_cert_data:
        spec["tlsClientCertData"] = tls_client_cert_data
    
    if tls_client_cert_key:
        spec["tlsClientCertKey"] = tls_client_cert_key
    
    if enable_oci:
        spec["enableOCI"] = enable_oci
    
    return spec


def extract_application_summary(app: Dict[str, Any]) -> Dict[str, Any]:
    """Extract summary information from application"""
    metadata = app.get('metadata', {})
    spec = app.get('spec', {})
    status = app.get('status', {})
    
    return {
        "name": metadata.get('name', ''),
        "project": spec.get('project', ''),
        "sync_status": status.get('sync', {}).get('status', 'Unknown'),
        "health_status": status.get('health', {}).get('status', 'Unknown'),
        "repo_url": spec.get('source', {}).get('repoURL', ''),
        "namespace": spec.get('destination', {}).get('namespace', ''),
        "created_at": metadata.get('creationTimestamp')
    }


def extract_project_summary(project: Dict[str, Any]) -> Dict[str, Any]:
    """Extract summary information from project"""
    metadata = project.get('metadata', {})
    spec = project.get('spec', {})
    
    return {
        "name": metadata.get('name', ''),
        "description": spec.get('description', ''),
        "source_repos_count": len(spec.get('sourceRepos', [])),
        "destinations_count": len(spec.get('destinations', []))
    }


def extract_repository_summary(repo: Dict[str, Any]) -> Dict[str, Any]:
    """Extract summary information from repository"""
    connection_state = repo.get('connectionState', {})
    
    return {
        "repo": repo.get('repo', ''),
        "type": repo.get('type', 'git'),
        "name": repo.get('name'),
        "connection_status": connection_state.get('status', 'Unknown')
    }


def extract_cluster_summary(cluster: Dict[str, Any]) -> Dict[str, Any]:
    """Extract summary information from cluster"""
    connection_state = cluster.get('connectionState', {})
    
    return {
        "server": cluster.get('server', ''),
        "name": cluster.get('name', ''),
        "status": connection_state.get('status', 'Unknown')
    }


def validate_k8s_name(name: str) -> bool:
    """Validate Kubernetes resource name"""
    # K8s names must be lowercase alphanumeric or '-', and start/end with alphanumeric
    pattern = r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
    return bool(re.match(pattern, name)) and len(name) <= 253


def sanitize_dict(data: Dict[str, Any], remove_none: bool = True) -> Dict[str, Any]:
    """Remove None values from dictionary"""
    if not remove_none:
        return data
    
    return {k: v for k, v in data.items() if v is not None}


def format_datetime(dt: Optional[str]) -> Optional[datetime]:
    """Parse datetime string to datetime object"""
    if not dt:
        return None
    
    try:
        return datetime.fromisoformat(dt.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None