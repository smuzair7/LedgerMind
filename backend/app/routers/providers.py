from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.middleware.provider_key import get_provider_key
from app.providers.catalog import PROVIDERS, by_id
from app.providers.registry import UnknownProviderError, build_provider
from app.schemas.providers import ProviderInfo, ValidateRequest, ValidateResponse

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderInfo])
async def list_providers() -> list[ProviderInfo]:
    return PROVIDERS


@router.get("/{provider_id}", response_model=ProviderInfo)
async def get_provider(provider_id: str) -> ProviderInfo:
    info = by_id(provider_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Unknown provider")
    return info


@router.post("/validate", response_model=ValidateResponse)
async def validate(payload: ValidateRequest, request: Request) -> ValidateResponse:
    key = get_provider_key(request)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Provider-Key header",
        )
    try:
        provider = build_provider(payload.provider, api_key=key, base_url=payload.base_url)
    except UnknownProviderError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    ok, detail = await provider.validate(model=payload.model)
    return ValidateResponse(ok=ok, detail=detail)
