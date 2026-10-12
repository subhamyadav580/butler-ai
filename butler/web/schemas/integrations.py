from typing import Literal, Optional

from pydantic import BaseModel


class IntegrationStatus(BaseModel):
    name: str
    title: str
    description: str
    state: Literal["connected", "disconnected", "needs_setup"]
    detail: str
    connecting: bool
    can_connect: bool = True       # False: set up in .env (API key), no login button
    error: Optional[str] = None
    expires_at: Optional[float] = None
    needs_reload: bool = False      # connected, but the agent must reload to use it


class IntegrationsResponse(BaseModel):
    integrations: list[IntegrationStatus]


class MetaResponse(BaseModel):
    """What the UI needs to know about integrations: no per-integration code."""
    tool_labels: dict[str, str]     # tool name → "Searching your mail"
    examples: list[str]             # example prompts for the empty chat


class WebSearchProvider(BaseModel):
    name: str
    title: str
    key_setting: str        # the .env variable for its API key
    configured: bool        # has an API key
    enabled: bool           # switched on in the UI
    primary: bool           # tried first right now


class WebSearchProvidersResponse(BaseModel):
    providers: list[WebSearchProvider]


class UpdateWebSearchRequest(BaseModel):
    enabled: dict[str, bool] = {}       # {"serper": false, …}: only the ones that change
    primary: Optional[str] = None       # provider to try first
