from fastapi import APIRouter, HTTPException

from satops_backend.schemas import Observation, ObservationBase
from satops_backend.services import observation

router = APIRouter(prefix="/observations", tags=["observations"])


@router.get("/")
async def list_observations(limit: int = 50) -> list[Observation]:
    return await observation.get_observations(limit=limit)


@router.get("/{observation_id}")
async def get_observation(observation_id: int) -> Observation:
    obs = await observation.get_observation(observation_id)
    if obs is None:
        raise HTTPException(status_code=404, detail="Observation not found")
    return obs


@router.post("/", status_code=201)
async def create_observation(obs: ObservationBase) -> Observation:
    return await observation.create_observation(obs)
