from typing import Literal, Optional

from pydantic import BaseModel


class IntegrationStatus(BaseModel):
    name: str
    title: str
    description: str
    state: Literal["connected", "disconnected", "needs_setup"]
    detail: str
    connecting: bool
    error: Optional[str] = None
    expires_at: Optional[float] = None


class IntegrationsResponse(BaseModel):
    integrations: list[IntegrationStatus]
    agent_has_swiggy: bool
