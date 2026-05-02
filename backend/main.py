from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import ALLOWED_ORIGINS, BENCHMARK_API_KEY
from database import init_db
from routes import profiles, subjects, interviews, query, review, admin, files
from routes.v1 import health as v1_health, query as v1_query, system as v1_system, knowledge as v1_knowledge
from routes.v1 import smes as v1_smes, interviews as v1_interviews

app = FastAPI(title="Project Thoth", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def benchmark_auth_middleware(request: Request, call_next):
    """Bearer token guard for the /api/v1 benchmark surface only.

    The internal /api/* routes used by our own frontend are unauthenticated
    (no real auth in this PoC). The benchmark evaluator hits /api/v1/* with
    `Authorization: Bearer <BENCHMARK_API_KEY>` — anything missing or wrong
    gets 401.

    OPTIONS requests are exempt so CORS preflight still works.
    """
    path = request.url.path or ""
    if path.startswith("/api/v1") and request.method != "OPTIONS":
        if BENCHMARK_API_KEY:
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"error": "Missing Bearer token", "code": "UNAUTHORIZED"},
                )
            if auth.split(" ", 1)[1] != BENCHMARK_API_KEY:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid API key", "code": "UNAUTHORIZED"},
                )
        # If BENCHMARK_API_KEY is empty (dev-only), let everything through.
    return await call_next(request)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Internal frontend-facing routes (unauthenticated).
app.include_router(profiles.router)
app.include_router(subjects.router)
app.include_router(interviews.router)
app.include_router(query.router)
app.include_router(review.router)
app.include_router(admin.router)
app.include_router(files.router)

# Benchmark API surface — auth-gated by the middleware above.
app.include_router(v1_health.router)
app.include_router(v1_query.router)
app.include_router(v1_system.router)
app.include_router(v1_knowledge.router)
app.include_router(v1_smes.router)
app.include_router(v1_interviews.router)
