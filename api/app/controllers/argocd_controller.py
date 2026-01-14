from typing import List, Optional
from fastapi import HTTPException, status

from app.services.argocd_service import ArgoCDService
from app.models.argocd import (
    ApplicationDeleteResponse,
    ApplicationListResponse,
    ApplicationQueryParams,
    ApplicationResponse,
    ApplicationSummaryResponse,
    ClusterListResponse,
    ClusterResponse,
    ClusterSummaryResponse,
    CreateApplicationRequest,
    CreateProjectRequest,
    CreateRepositoryRequest,
    ProjectResponse,
    ProjectSummaryResponse,
    ProjectListResponse,
    RepositoryListResponse,
    RepositorySummaryResponse,
    RollbackApplicationRequest,
    SyncApplicationRequest,
    SyncOperationResponse,
    UpdateApplicationRequest
)
from app.models.common import BaseResponse, ResponseStatus
from app.core.exceptions import ApplicationNotFoundException, ProjectNotFoundException, ArgoCDAPIException

class ArgoCDController:

    # ==================== Application Operations ====================
    """Controller for application operations"""
    @staticmethod
    async def list_applications(
        service: ArgoCDService,
        query_params: ApplicationQueryParams
    ) -> ApplicationListResponse:
        """List all applications with optional filtering"""
        try:
            apps = service.list_applications(project=query_params.project)
            
            # Apply filters
            if query_params.sync_status:
                apps = [app for app in apps if app['sync_status'] == query_params.sync_status]
            
            if query_params.health_status:
                apps = [app for app in apps if app['health_status'] == query_params.health_status]
            
            if query_params.repo:
                apps = [app for app in apps if query_params.repo in app.get('repo_url', '')]
            
            return ApplicationListResponse(
                items=[ApplicationSummaryResponse(**app) for app in apps],
                total=len(apps)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list applications: {str(e)}"
            )
    
    @staticmethod
    async def get_application(
        service: ArgoCDService,
        app_name: str
    ) -> ApplicationResponse:
        """Get application details"""
        try:
            app = service.get_application(app_name)
            return ApplicationResponse(**app)
        except ApplicationNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get application: {str(e)}"
            )
    
    @staticmethod
    async def create_application(
        service: ArgoCDService,
        request: CreateApplicationRequest
    ) -> BaseResponse:
        """Create a new application"""
        try:
            app = service.create_application(
                name=request.name,
                project=request.project,
                repo_url=request.repo_url,
                path=request.path,
                target_revision=request.target_revision,
                destination_server=request.destination_server,
                destination_namespace=request.destination_namespace,
                auto_sync=request.auto_sync,
                auto_prune=request.auto_prune,
                self_heal=request.self_heal,
                chart=request.chart,
                helm_values=request.helm_values,
                labels=request.labels,
                annotations=request.annotations
            )
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message=f"Application '{request.name}' created successfully",
                data=app
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create application: {str(e)}"
            )
    
    @staticmethod
    async def update_application(
        service: ArgoCDService,
        app_name: str,
        request: UpdateApplicationRequest
    ) -> BaseResponse:
        """Update an existing application"""
        try:
            updates = request.model_dump(exclude_none=True)
            
            if not updates:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No updates provided"
                )
            
            app = service.update_application(app_name, updates)
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message=f"Application '{app_name}' updated successfully",
                data=app
            )
        except ApplicationNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to update application: {str(e)}"
            )
    
    @staticmethod
    async def delete_application(
        service: ArgoCDService,
        app_name: str,
        cascade: bool = False
    ) -> ApplicationDeleteResponse:
        """Delete an application"""
        try:
            result = service.delete_application(app_name, cascade=cascade)
            
            return ApplicationDeleteResponse(
                application=app_name,
                deleted=True,
                cascade=cascade,
                message=f"Application '{app_name}' deleted successfully"
            )
        except ApplicationNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to delete application: {str(e)}"
            )
    
    @staticmethod
    async def sync_application(
        service: ArgoCDService,
        app_name: str,
        request: SyncApplicationRequest
    ) -> SyncOperationResponse:
        """Sync an application"""
        try:
            result = service.sync_application(
                app_name=app_name,
                revision=request.revision,
                prune=request.prune,
                dry_run=request.dry_run,
                resources=request.resources
            )
            
            return SyncOperationResponse(
                application=app_name,
                status="initiated" if not request.dry_run else "dry_run",
                message=f"Sync {'dry run' if request.dry_run else 'operation'} initiated for '{app_name}'"
            )
        except ApplicationNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to sync application: {str(e)}"
            )
    
    @staticmethod
    async def rollback_application(
        service: ArgoCDService,
        app_name: str,
        request: RollbackApplicationRequest
    ) -> BaseResponse:
        """Rollback application to a specific revision"""
        try:
            result = service.rollback_application(app_name, request.revision)
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message=f"Application '{app_name}' rollback to revision '{request.revision}' initiated",
                data=result
            )
        except ApplicationNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to rollback application: {str(e)}"
            )
    
    @staticmethod
    async def refresh_application(
        service: ArgoCDService,
        app_name: str
    ) -> BaseResponse:
        """Refresh application"""
        try:
            result = service.refresh_application(app_name)
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message=f"Application '{app_name}' refreshed successfully",
                data=result
            )
        except ApplicationNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to refresh application: {str(e)}"
            )
    
    @staticmethod
    async def get_application_status(
        service: ArgoCDService,
        app_name: str
    ) -> BaseResponse:
        """Get application status"""
        try:
            status_data = service.get_application_status(app_name)
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                data=status_data
            )
        except ApplicationNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get application status: {str(e)}"
            )
    
    @staticmethod
    async def get_out_of_sync_applications(
        service: ArgoCDService,
        project: Optional[str] = None
    ) -> ApplicationListResponse:
        """Get all out-of-sync applications"""
        try:
            apps = service.get_out_of_sync_applications(project)
            
            return ApplicationListResponse(
                items=[ApplicationSummaryResponse(**app) for app in apps],
                total=len(apps)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get out-of-sync applications: {str(e)}"
            )
    
    @staticmethod
    async def get_unhealthy_applications(
        service: ArgoCDService,
        project: Optional[str] = None
    ) -> ApplicationListResponse:
        """Get all unhealthy applications"""
        try:
            apps = service.get_unhealthy_applications(project)
            
            return ApplicationListResponse(
                items=[ApplicationSummaryResponse(**app) for app in apps],
                total=len(apps)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get unhealthy applications: {str(e)}"
            )
    
    @staticmethod
    async def sync_all_out_of_sync(
        service: ArgoCDService,
        project: Optional[str] = None,
        prune: bool = True
    ) -> BaseResponse:
        """Sync all out-of-sync applications"""
        try:
            results = service.sync_all_out_of_sync_applications(project, prune)
            
            success_count = sum(1 for r in results if r['status'] == 'synced')
            failed_count = len(results) - success_count
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message=f"Synced {success_count} applications, {failed_count} failed",
                data={
                    'total': len(results),
                    'success': success_count,
                    'failed': failed_count,
                    'results': results
                }
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to sync applications: {str(e)}"
            )
        

    # ==================== Project Operations ====================
    @staticmethod
    async def list_projects(service: ArgoCDService) -> ProjectListResponse:
        """List all projects"""
        try:
            projects = service.list_projects()
            
            return ProjectListResponse(
                items=[ProjectSummaryResponse(**proj) for proj in projects],
                total=len(projects)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list projects: {str(e)}"
            )
    
    @staticmethod
    async def get_project(
        service: ArgoCDService,
        project_name: str
    ) -> ProjectResponse:
        """Get project details"""
        try:
            project = service.get_project(project_name)
            return ProjectResponse(**project)
        except ProjectNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get project: {str(e)}"
            )
    
    @staticmethod
    async def create_project(
        service: ArgoCDService,
        request: CreateProjectRequest
    ) -> BaseResponse:
        """Create a new project"""
        try:
            project = service.create_project(
                name=request.name,
                description=request.description,
                source_repos=request.source_repos,
                destinations=request.destinations,
                cluster_resource_whitelist=request.cluster_resource_whitelist,
                namespace_resource_blacklist=request.namespace_resource_blacklist,
                roles=request.roles
            )
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message=f"Project '{request.name}' created successfully",
                data=project
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create project: {str(e)}"
            )
    
    @staticmethod
    async def delete_project(
        service: ArgoCDService,
        project_name: str
    ) -> BaseResponse:
        """Delete a project"""
        try:
            service.delete_project(project_name)
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message=f"Project '{project_name}' deleted successfully"
            )
        except ProjectNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to delete project: {str(e)}"
            )

    # ==================== Repository Operations ====================    
    @staticmethod
    async def list_repositories(service: ArgoCDService) -> RepositoryListResponse:
        """List all repositories"""
        try:
            repos = service.list_repositories()
            
            return RepositoryListResponse(
                items=[RepositorySummaryResponse(**repo) for repo in repos],
                total=len(repos)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list repositories: {str(e)}"
            )
    
    @staticmethod
    async def create_repository(
        service: ArgoCDService,
        request: CreateRepositoryRequest
    ) -> BaseResponse:
        """Add a new repository"""
        try:
            repo = service.create_repository(
                repo_url=request.repo_url,
                repo_type=request.type,
                name=request.name,
                username=request.username,
                password=request.password,
                ssh_private_key=request.ssh_private_key,
                insecure=request.insecure,
                tls_client_cert_data=request.tls_client_cert_data,
                tls_client_cert_key=request.tls_client_cert_key,
                enable_oci=request.enable_oci
            )
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message=f"Repository '{request.repo_url}' added successfully",
                data=repo
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to add repository: {str(e)}"
            )
    
    @staticmethod
    async def delete_repository(
        service: ArgoCDService,
        repo_url: str
    ) -> BaseResponse:
        """Remove a repository"""
        try:
            service.delete_repository(repo_url)
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message=f"Repository '{repo_url}' removed successfully"
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to remove repository: {str(e)}"
            )
    
    # ==================== Cluster Operations ====================    
    @staticmethod
    async def list_clusters(service: ArgoCDService) -> ClusterListResponse:
        """List all clusters"""
        try:
            clusters = service.list_clusters()
            
            return ClusterListResponse(
                items=[ClusterSummaryResponse(**cluster) for cluster in clusters],
                total=len(clusters)
            )
        except ArgoCDAPIException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list clusters: {str(e)}"
            )
    
    @staticmethod
    async def get_cluster(
        service: ArgoCDService,
        cluster_url: str
    ) -> ClusterResponse:
        """Get cluster details"""
        try:
            cluster = service.get_cluster(cluster_url)
            return ClusterResponse(**cluster)
        except ArgoCDAPIException as e:
            if e.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Cluster '{cluster_url}' not found"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get cluster: {str(e)}"
            )