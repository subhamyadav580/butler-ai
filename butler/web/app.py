"""FastAPI application: JSON/SSE API under /api, React UI everywhere else."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from butler.config import DATABASE_PATH, FRONTEND_DIST
from butler.web.db import Database
from butler.web.repos import MessageRepo, ThreadRepo
from butler.web.routes import auth, chat, integrations
from butler.web.services.agent_service import AgentService
from butler.web.services.chat_service import ChatService
from butler.web.services.integration_service import IntegrationService


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_service = AgentService()
    await agent_service.start()

    async def on_connected(name):
        # New credentials → rebuild the agent so it picks up the new tools
        if name == "swiggy":
            await agent_service.reload()

    # Chat list + transcripts persist in SQLite; agent memory stays in RAM
    database = Database(DATABASE_PATH)
    database.init_schema()

    app.state.agent_service = agent_service
    app.state.chat_service = ChatService(
        agent_service, ThreadRepo(database), MessageRepo(database)
    )
    app.state.integration_service = IntegrationService(on_connected=on_connected)
    yield
    database.close()


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

    # Built assets have content hashes in their names (index-3fa9c1.css), so
    # browsers may cache them forever; a new build gets new names.
    app.mount("/assets", ImmutableStaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    # Single-page app: any non-API path returns index.html. It must be
    # revalidated on every load, or browsers keep showing an old build.
    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        file = FRONTEND_DIST / path
        if path and file.is_file() and FRONTEND_DIST in file.resolve().parents:
            return FileResponse(file, headers=NO_CACHE)
        return FileResponse(index, headers=NO_CACHE)


NO_CACHE = {"Cache-Control": "no-cache"}


class ImmutableStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


app = create_app()
