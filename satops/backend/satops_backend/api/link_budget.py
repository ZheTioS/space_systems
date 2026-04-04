from fastapi import APIRouter

from satops_backend.services.link_budget import LinkBudgetInput, LinkBudgetOutput, compute_link_budget

router = APIRouter(prefix="/link-budget", tags=["link-budget"])


@router.post("/compute")
async def compute(params: LinkBudgetInput) -> LinkBudgetOutput:
    """Compute link budget from parameters."""
    return compute_link_budget(params)
