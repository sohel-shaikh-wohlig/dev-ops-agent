"""
Terraform Automation Routes
FastAPI endpoints for Terraform resource provisioning via GitOps

Endpoint: POST /terraform/provision

Renders a Terraform template, pushes the rendered file to a feature branch
in the target Terraform repo, and opens a Pull Request so Atlantis can
auto-plan the change.
"""

from fastapi import APIRouter, status

from app.controllers.terraform_controller import terraform_controller
from app.models.terraform import (
    TerraformProvisionRequest,
    TerraformProvisionResponse,
)
from app.models.common import ErrorResponse

router = APIRouter(prefix="/terraform", tags=["Terraform Automation"])


@router.post(
    "/provision",
    response_model=TerraformProvisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Provision Terraform Resource via GitOps PR",
    description=(
        "Renders a Terraform template for the given resource_type, pushes "
        "the result to a feature branch in the Terraform repo, and opens a "
        "Pull Request so Atlantis can auto-plan the change."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Client config or environment error"},
        404: {"model": ErrorResponse, "description": "Template or config file not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def provision_resource(
    request: TerraformProvisionRequest,
) -> TerraformProvisionResponse:
    """
    **Provision a Terraform resource via GitOps**

    Renders the .tf template for `resource_type`, pushes it to a feature
    branch in the Terraform repo, and opens a Pull Request for Atlantis
    to auto-plan.
    """
    return await terraform_controller.provision(request)
