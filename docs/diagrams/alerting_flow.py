#!/usr/bin/env python3
"""Render the signal -> alert lifecycle as alerting_flow.png.

Traces one telemetry signal end to end, exactly as wired in this repo:

    instrument (prometheus_client counter/histogram/gauge)
      -> Prometheus scrapes /metrics
      -> recording rules pre-compute SLIs (error ratio over 5m/30m/1h/6h)
      -> multi-window multi-burn-rate alerts evaluate
      -> ErrorBudgetBurnFast (14.4x, page) / ErrorBudgetBurnSlow (6x, ticket) fire
      -> Alertmanager routes / groups / inhibits
      -> notify receivers.

Usage:  python alerting_flow.py   ->   alerting_flow.png  (needs Graphviz `dot`)

Author: Md Irshad - Senior Cloud & AI Platform Engineer
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.monitoring import Prometheus
from diagrams.programming.framework import Fastapi
from diagrams.programming.flowchart import Decision
from diagrams.generic.blank import Blank

# Alertmanager icon exists only in newer `diagrams` releases; fall back to the
# Prometheus-family icon so this renders regardless of installed version.
try:  # pragma: no cover - purely cosmetic icon selection
    from diagrams.onprem.monitoring import Alertmanager
except ImportError:  # pragma: no cover
    Alertmanager = Prometheus

graph_attr = {
    "fontsize": "20",
    "labelloc": "t",
    "bgcolor": "white",
    "pad": "0.6",
    "splines": "spline",
}

with Diagram(
    "Observability Stack - Signal to Alert Lifecycle",
    filename="alerting_flow",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    app = Fastapi("instrument\nhttp_requests_total\nhttp_request_duration_seconds")

    prom = Prometheus("Prometheus\nscrape /metrics 15s")

    with Cluster("Recording rules (SLIs)"):
        r5m = Blank("error_ratio:rate5m_bw")
        r30m = Blank("error_ratio:rate30m")
        r1h = Blank("error_ratio:rate1h")
        r6h = Blank("error_ratio:rate6h")

    with Cluster("Multi-window multi-burn-rate eval"):
        fast = Decision("Fast: 1h AND 5m\n> 14.4 x 1%")
        slow = Decision("Slow: 6h AND 30m\n> 6 x 1%")

    with Cluster("Alerts fire"):
        page = Blank("ErrorBudgetBurnFast\ncritical -> page")
        ticket = Blank("ErrorBudgetBurnSlow\nwarning -> ticket")

    alertmgr = Alertmanager("Alertmanager\nroute / group / inhibit")

    with Cluster("Notify"):
        webhook = Blank("webhook (default)")
        slack = Blank("Slack / PagerDuty\n(documented)")

    app >> Edge(label="scrape") >> prom
    prom >> Edge(label="evaluate") >> [r5m, r30m, r1h, r6h]

    r1h >> fast
    r5m >> fast
    r6h >> slow
    r30m >> slow

    fast >> Edge(color="firebrick", label="for 2m") >> page
    slow >> Edge(color="darkorange", label="for 15m") >> ticket

    page >> Edge(color="firebrick") >> alertmgr
    ticket >> Edge(color="darkorange") >> alertmgr

    alertmgr >> Edge(label="notify") >> webhook
    alertmgr >> Edge(style="dotted") >> slack
