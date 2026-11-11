"""FastAPI entrypoint. Keep this thin: routers for store, agent, channels and console mount here."""
import time

from fastapi import FastAPI

from app import llm

app = FastAPI(title="Kavach", version="0.1.0")
_started = time.time()


@app.get("/health")
def health() -> dict:
    """Cheap liveness probe for uptime monitors. Never calls a paid API and never returns secrets."""
    counts: dict[str, int] = {}
    for p in llm.providers():
        counts[p.name] = counts.get(p.name, 0) + 1
    return {"status": "ok", "version": app.version, "uptime_s": int(time.time() - _started), "llm_keys": counts}
