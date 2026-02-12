"""
Terraform Controller
Handles request validation, delegates to TerraformService,
and formats HTTP responses / errors.
"""

from fastapi import HTTPException, status

from app.core.logging_config import logger
from app.models.terraform import (
    TerraformProvisionRequest,
    TerraformProvisionResponse,
)
from app.services.terraform_service import TerraformService


class TerraformController:
    """Controller for Terraform provisioning endpoints."""

    def __init__(self) -> None:
        self.service = TerraformService()
        logger.info("TerraformController initialized")

    async def provision(
        self, request: TerraformProvisionRequest
    ) -> TerraformProvisionResponse:
        """
        Handle a Terraform provisioning request via GitOps.

        Renders the template, pushes to a feature branch, and opens a PR.

        Args:
            request: Validated TerraformProvisionRequest

        Returns:
            TerraformProvisionResponse with branch and PR URL

        Raises:
            HTTPException on validation / processing errors
        """
        try:
            result = await self.service.provision(request)

            return TerraformProvisionResponse(
                status=result["status"],
                message=result["message"],
                resource_type=result["resource_type"],
                environment=result["environment"],
                branch=result.get("branch"),
                pr_url=result.get("pr_url"),
            )

        except FileNotFoundError as e:
            logger.warning(f"Terraform provision — not found: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        except KeyError as e:
            logger.warning(f"Terraform provision — config error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        except ValueError as e:
            logger.warning(f"Terraform provision — validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )

        except RuntimeError as e:
            logger.error(f"Terraform provision — git/PR error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

        except Exception as e:
            logger.error(
                f"Terraform provision — unexpected error: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process Terraform request: {str(e)}",
            )


# Singleton instance
terraform_controller = TerraformController()
