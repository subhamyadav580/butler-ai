from fastapi import Depends, HTTPException, status

from butler.web.dependencies import get_agent_service, get_integration_service
from butler.web.schemas.integrations import IntegrationsResponse
from butler.web.services.agent_service import AgentService
from butler.web.services.integration_service import (
    IntegrationService,
    UnknownIntegration,
)


async def list_integrations(
    integrations: IntegrationService = Depends(get_integration_service),
    agent: AgentService = Depends(get_agent_service),
) -> IntegrationsResponse:
    return IntegrationsResponse(
        integrations=integrations.list_status(agent.swiggy_loaded),
        agent_has_swiggy=agent.swiggy_loaded,
    )


async def connect_integration(
    name: str,
    integrations: IntegrationService = Depends(get_integration_service),
):
    try:
        integrations.connect(name)
    except UnknownIntegration:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown integration: {name}")
    return {"started": True}


async def reload_agent(agent: AgentService = Depends(get_agent_service)):
    await agent.reload()
    return {"ok": True, "agent_has_swiggy": agent.swiggy_loaded}
