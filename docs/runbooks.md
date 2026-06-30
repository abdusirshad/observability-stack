# Runbooks

Operational runbooks referenced by the `runbook_url` annotation on each alert.
These are intentionally concise - they describe the diagnosis path for the demo
stack, mirroring how a real on-call runbook is structured.

---

## Error budget burn

**Alerts:** `ErrorBudgetBurnFast` (critical, page), `ErrorBudgetBurnSlow` (warning, ticket)

The service is returning 5xx responses fast enough to threaten the 30-day
availability SLO (99% success / 1% error budget).

1. Confirm scope in Grafana -> *Sample App - RED / SLO* -> "Error ratio vs SLO budget".
2. Check which path is failing: `sum by (path,status) (rate(http_requests_total{service="sample-app"}[5m]))`.
3. For the demo, `/error` returns 500 ~30% of the time by design - generating
   load with `make load` will trip `ErrorBudgetBurnFast`. In production this maps
   to a bad deploy, dependency outage, or saturation.
4. Mitigation: roll back the last deploy, fail over the unhealthy dependency, or
   shed load. Re-check the burn rate has dropped below threshold.

---

## Latency SLO breach

**Alert:** `LatencySLOBreachP99` (warning)

p99 request latency exceeded the 500ms SLO over a 5m window.

1. Grafana -> "Latency p50 / p99 vs SLO". Is it broad or one path?
2. Correlate with saturation: "in-flight requests & node CPU" panel.
3. The `/work` endpoint sleeps a random amount; heavy `make load` pushes p99 up.
   In production: check GC pauses, slow downstream calls, CPU throttling.

---

## Target down

**Alert:** `TargetDown` (critical)

Prometheus cannot scrape a target for >1m.

1. `docker compose ps` - is the container up and healthy?
2. `docker compose logs <service>`.
3. Prometheus -> Status -> Targets shows the scrape error.

---

## High node CPU / low disk

**Alerts:** `HighNodeCpuUsage`, `LowDiskSpace` (warning)

Host-level saturation from `node-exporter`. Identify the offending process,
scale out, or free disk. On a laptop these are informational.
