from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    UserRequest,
    ScoredOptionSchema,
    RecommendationResponse,
)
from app.logic import get_ranked_options, get_recommendation


app = FastAPI(
    title="Solar Share Backend",
    description="Decision engine for local clean energy optimization",
    version="0.1.0",
)

# CORS: allow frontend apps to talk to this API
# For now we allow all origins; later this will be locked down
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "Solar Share backend is running",
        "version": "0.1.0",
    }


@app.post("/options", response_model=List[ScoredOptionSchema])
def options(request: UserRequest):
    return get_ranked_options(request)


@app.post("/recommendation", response_model=RecommendationResponse)
def recommendation(request: UserRequest):
    return get_recommendation(request)