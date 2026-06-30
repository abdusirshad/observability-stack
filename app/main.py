"""Instrumented sample service for the observability stack.

A tiny FastAPI app that emits the three core Prometheus metric types so the
Prometheus rules, Alertmanager routes and Grafana dashboards in this repo have
real data to operate on:

    * Counter   - http_requests_total          (RED: Rate + Errors)
    * Histogram - http_request_duration_seconds (RED: Duration / latency)
    * Gauge     - app_inprogress_requests       (concurrency / saturation)

Endpoints
---------
    GET /         - cheap endpoint, always 200
    GET /work     - simulated work with variable latency (200)
    GET /error    - returns 500 ~30% of the time to exercise error-rate SLOs
    GET /healthz  - liveness probe (excluded from request metrics)
    GET /metrics  - Prometheus exposition format

Author: Md Irshad - Senior Cloud & AI Platform Engineer
"""
from __future__ import annotations

import os
import random
import time

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# A dedicated registry keeps the exposition output deterministic and free of
# unrelated default process collectors that would add noise to the demo.
REGISTRY = CollectorRegistry()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests processed, partitioned by method, path and status.",
    labelnames=("method", "path", "status"),
    registry=REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    labelnames=("method", "path"),
    # Buckets tuned for a sub-second web service so p99 latency SLOs are useful.
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY,
)

INPROGRESS = Gauge(
    "app_inprogress_requests",
    "Number of in-flight HTTP requests (saturation signal).",
    registry=REGISTRY,
)

app = FastAPI(title="observability-stack sample app", version="1.0.0")

# Paths that should not pollute request/SLO metrics.
_EXCLUDED_PATHS = {"/metrics", "/healthz"}


@app.middleware("http")
async def instrument(request: Request, call_next):
    """Record count, latency and in-flight gauge for every business request."""
    path = request.url.path
    if path in _EXCLUDED_PATHS:
        return await call_next(request)

    method = request.method
    INPROGRESS.inc()
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed = time.perf_counter() - start
        INPROGRESS.dec()
        REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
        REQUEST_COUNT.labels(
            method=method, path=path, status=str(status_code)
        ).inc()


@app.get("/")
async def root() -> JSONResponse:
    """Cheap always-200 endpoint."""
    return JSONResponse({"service": "sample-app", "status": "ok"})


@app.get("/work")
async def work() -> JSONResponse:
    """Simulate variable-latency work to populate the latency histogram."""
    # Log-normal-ish spread so most requests are fast and a few are slow.
    delay = min(random.expovariate(20.0), 2.0)
    time.sleep(delay)
    return JSONResponse({"slept_seconds": round(delay, 4)})


@app.get("/error")
async def maybe_error() -> Response:
    """Return HTTP 500 ~30% of the time to drive error-rate / burn-rate alerts."""
    if random.random() < 0.30:
        return JSONResponse({"error": "synthetic failure"}, status_code=500)
    return JSONResponse({"status": "ok"})


@app.get("/healthz")
async def healthz() -> PlainTextResponse:
    """Liveness/readiness probe - intentionally excluded from metrics."""
    return PlainTextResponse("ok")


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus exposition endpoint."""
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
