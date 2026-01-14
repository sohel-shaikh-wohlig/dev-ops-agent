
from fastapi import HTTPException, status


class ArgoCDException(Exception):
    """Base exception for ArgoCD operations"""
    pass


class TokenExpiredException(ArgoCDException):
    """Raised when ArgoCD token is expired"""
    pass


class TokenRenewalFailedException(ArgoCDException):
    """Raised when token renewal fails"""
    pass


class ApplicationNotFoundException(ArgoCDException):
    """Raised when application is not found"""
    pass


class ProjectNotFoundException(ArgoCDException):
    """Raised when project is not found"""
    pass


class RepositoryNotFoundException(ArgoCDException):
    """Raised when repository is not found"""
    pass


class SyncFailedException(ArgoCDException):
    """Raised when application sync fails"""
    pass


class ArgoCDAPIException(ArgoCDException):
    """Raised when ArgoCD API returns an error"""
    
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)


# HTTP Exception helpers
def http_exception(status_code: int, detail: str) -> HTTPException:
    """Create HTTP exception"""
    return HTTPException(status_code=status_code, detail=detail)


def not_found_exception(resource: str, identifier: str) -> HTTPException:
    """Create 404 not found exception"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} '{identifier}' not found"
    )


def bad_request_exception(detail: str) -> HTTPException:
    """Create 400 bad request exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail
    )


def unauthorized_exception(detail: str = "Unauthorized") -> HTTPException:
    """Create 401 unauthorized exception"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail
    )


def internal_server_exception(detail: str = "Internal server error") -> HTTPException:
    """Create 500 internal server error exception"""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail
    )
