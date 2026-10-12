from fastapi import Depends, HTTPException, status

from butler.web.dependencies import get_agent_service, get_integration_service
from butler.integrations.registry import all_tool_labels, example_prompts
from butler.integrations.websearch import provider_overview, save_preferences
from butler.web.schemas.integrations import (
    IntegrationsResponse,
    MetaResponse,
    UpdateWebSearchRequest,
    WebSearchProvidersResponse,
)
from butler.web.services.agent_service import AgentService
from butler.web.services.integration_service import (
    IntegrationService,
    UnknownIntegration,
)


async def list_integrations(
    integrations: IntegrationService = Depends(get_integration_service),
    agent: AgentService = Depends(get_agent_service),
) -> IntegrationsResponse:
    return IntegrationsResponse(integrations=integrations.list_status(agent.tool_names))


async def connect_integration(
    name: str,
    integrations: IntegrationService = Depends(get_integration_service),
):
    try:
        integrations.connect(name)
    except UnknownIntegration:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown integration: {name}") from None
    return {"started": True}


async def reload_agent(agent: AgentService = Depends(get_agent_service)):
    await agent.reload()
    return {"ok": True}


async def get_web_search_providers() -> WebSearchProvidersResponse:
    return WebSearchProvidersResponse(providers=provider_overview())


async def update_web_search_providers(request: UpdateWebSearchRequest) -> WebSearchProvidersResponse:
    try:
        save_preferences(request.enabled, request.primary)
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    return WebSearchProvidersResponse(providers=provider_overview())


async def get_meta() -> MetaResponse:
    return MetaResponse(tool_labels=all_tool_labels(), examples=example_prompts())
