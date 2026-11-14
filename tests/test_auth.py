import pytest
from fastapi import HTTPException

from src.api.dependencies import require_auth
from src.core.config import settings


@pytest.mark.asyncio
async def test_auth_resolves_tenant_from_secret(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_keys", "acme:secret-a,other:secret-b")
    assert await require_auth("Bearer secret-a") == "acme"


@pytest.mark.asyncio
async def test_invalid_secret_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_keys", "acme:secret-a")
    with pytest.raises(HTTPException) as error:
        await require_auth("Bearer wrong")
    assert error.value.status_code == 401
