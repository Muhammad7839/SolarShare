"""Local executable entrypoint for running the SolarShare FastAPI service."""

import os

import uvicorn


def _as_bool(value: str) -> bool:
    """Parse common truthy string values for local run-time flags."""
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("SOLAR_SHARE_HOST", "127.0.0.1"),
        port=int(os.getenv("SOLAR_SHARE_PORT", "8000")),
        reload=_as_bool(os.getenv("SOLAR_SHARE_RELOAD", "1")),
    )
