from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import ALLOWED_ORIGINS
from database import init_db
from routes import profiles, subjects, interviews, query, review, admin, files

app = FastAPI(title="Project Thoth", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(profiles.router)
app.include_router(subjects.router)
app.include_router(interviews.router)
app.include_router(query.router)
app.include_router(review.router)
app.include_router(admin.router)
app.include_router(files.router)
