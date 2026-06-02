from __future__ import annotations

from fastapi import APIRouter, Depends
from publishr_schema import Plan

from ..deps import get_repository
from ..errors import NotFoundError
from ..repositories.protocol import RepositoryProtocol

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[Plan])
def list_plans(repo: RepositoryProtocol = Depends(get_repository)) -> list[Plan]:
    return repo.list_plans()


@router.get("/{plan_id}", response_model=Plan)
def get_plan(plan_id: str, repo: RepositoryProtocol = Depends(get_repository)) -> Plan:
    plan = repo.get_plan(plan_id)
    if plan is None:
        raise NotFoundError(f"plan {plan_id} が見つかりません")
    return plan
