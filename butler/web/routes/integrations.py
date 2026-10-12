from fastapi import APIRouter, Depends

from butler.web.dependencies import require_auth
from butler.web.handlers import integrations

router = APIRouter(
    prefix="/api/integrations", tags=["integrations"], dependencies=[Depends(require_auth)]
)

router.add_api_route("", integrations.list_integrations, methods=["GET"])
router.add_api_route("/meta", integrations.get_meta, methods=["GET"])
router.add_api_route("/web-search", integrations.get_web_search_providers, methods=["GET"])
router.add_api_route("/web-search", integrations.update_web_search_providers, methods=["PUT"])
router.add_api_route("/{name}/connect", integrations.connect_integration, methods=["POST"])
router.add_api_route("/reload", integrations.reload_agent, methods=["POST"])
