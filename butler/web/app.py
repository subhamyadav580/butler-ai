"""FastAPI application: JSON/SSE API under /api, React UI everywhere else."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from butler.config import FRONTEND_DIST
from butler.web.routes import auth, chat, integrations
from butler.web.services.agent_service import AgentService
from butler.web.services.integration_service import IntegrationService


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_service = AgentService()
    await agent_service.start()

    async def on_connected(name):
        # New credentials → rebuild the agent so it picks up the new tools
        if name == "swiggy":
            await agent_service.reload()

    app.state.agent_service = agent_service
    app.state.integration_service = IntegrationService(on_connected=on_connected)
    yield


def create_app():
    app = FastAPI(title="Butler", lifespan=lifespan)

    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(integrations.router)

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    _serve_frontend(app)
    return app


def _serve_frontend(app):
    index = FRONTEND_DIST / "index.html"

    if not index.exists():
        @app.get("/")
        async def frontend_missing():
            return JSONResponse({
                "message": "Frontend not built. Run: cd frontend && npm install && npm run build "
                           "(or `npm run dev` for development on http://localhost:5173)."
            })
        return

    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    # Single-page app: any non-API path returns index.html
    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        file = FRONTEND_DIST / path
        if path and file.is_file() and FRONTEND_DIST in file.resolve().parents:
            return FileResponse(file)
        return FileResponse(index)


app = create_app()
