from __future__ import annotations

from fastapi import APIRouter, Depends
from publishr_schema import Persona

from ..deps import get_repository
from ..errors import NotFoundError
from ..repositories.protocol import RepositoryProtocol

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("", response_model=list[Persona])
def list_personas(repo: RepositoryProtocol = Depends(get_repository)) -> list[Persona]:
    return repo.list_personas()


@router.get("/{persona_id}", response_model=Persona)
def get_persona(
    persona_id: str, repo: RepositoryProtocol = Depends(get_repository)
) -> Persona:
    persona = repo.get_persona(persona_id)
    if persona is None:
        raise NotFoundError(f"persona {persona_id} が見つかりません")
    return persona
