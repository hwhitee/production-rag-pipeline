import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.session import get_db


async def require_auth(authorization: Annotated[str | None, Header()] = None) -> str:
    tenant_keys = settings.tenant_api_keys
    if not tenant_keys:
        raise HTTPException(status_code=503, detail="Set API_KEYS as tenant-id:secret entries")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    for tenant_id, secret in tenant_keys.items():
        if hmac.compare_digest(token, secret):
            return tenant_id
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_tenant_id(tenant_id: Annotated[str, Depends(require_auth)]) -> str:
    return tenant_id


DbSession = Annotated[AsyncSession, Depends(get_db)]
TenantId = Annotated[str, Depends(get_tenant_id)]
