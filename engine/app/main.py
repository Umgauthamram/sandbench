"""Optional health endpoint for the engine. The worker is the real workhorse."""
from fastapi import FastAPI

app = FastAPI(title="SandBench Engine")


@app.get("/health")
def health():
    return {"ok": True, "service": "engine"}
