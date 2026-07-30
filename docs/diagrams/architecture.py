#!/usr/bin/env python3
"""Render the observability-stack scrape/serve topology as architecture.png.

Depicts the real docker-compose services and wiring in this repo:

    * sample-app (:8000, /metrics) + node-exporter (:9100) + Prometheus self
      (:9090)  are scraped by Prometheus.
    * Prometheus (:9090) loads recording + alerting rules and pushes firing
      alerts to Alertmanager (:9093).
    * Alertmanager routes/groups/inhibits and notifies receivers
      (webhook by default; Slack / PagerDuty documented).
    * Grafana (:3000) queries the Prometheus datasource and auto-provisions the
      RED / SLO dashboard.

All of it runs in a single docker-compose project on one bridge network.

Usage:  python architecture.py   ->   architecture.png  (needs Graphviz `dot`)

Author: Md Irshad - Senior Cloud & AI Platform Engineer
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.programming.framework import Fastapi
from diagrams.generic.blank import Blank

# `diagrams` ships an Alertmanager / node-exporter icon only in newer releases.
# Fall back to the Prometheus-family icon (same ecosystem) so this renders on
# both old and new versions without a hard dependency pin.
try:  # pragma: no cover - purely cosmetic icon selection
    from diagrams.onprem.monitoring import Alertmanager
except ImportError:  # pragma: no cover
    Alertmanager = Prometheus
try:  # pragma: no cover
    from diagrams.onprem.exporters import Node as NodeExporter
except ImportError:  # pragma: no cover
    NodeExporter = Prometheus

graph_attr = {
    "fontsize": "20",
    "labelloc": "t",
    "bgcolor": "white",
    "pad": "0.6",
    "splines": "spline",
}

with Diagram(
    "Observability Stack - Scrape & Serve Topology",
    filename="architecture",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    with Cluster("docker-compose project: observability-stack (bridge net: obs)"):

        with Cluster("Scrape targets"):
            app = Fastapi("sample-app :8000\n/metrics")
            node = NodeExporter("node-exporter :9100")

        prom = Prometheus("Prometheus :9090\nrecording + alert rules\n15d TSDB")
        alertmgr = Alertmanager("Alertmanager :9093\nroute / group / inhibit")
        grafana = Grafana("Grafana :3000\nRED / SLO dashboard")

        with Cluster("Receivers"):
            webhook = Blank("webhook (default)")
            slack = Blank("Slack (documented)")
            pagerduty = Blank("PagerDuty (documented)")

        # Scrapes (Prometheus pulls /metrics every 15s, including itself).
        app >> Edge(label="scrape 15s") >> prom
        node >> Edge(label="scrape 15s") >> prom
        prom >> Edge(label="self-scrape", style="dashed") >> prom

        # Alerts.
        prom >> Edge(label="fire alerts", color="firebrick") >> alertmgr
        alertmgr >> Edge(label="notify") >> webhook
        alertmgr >> Edge(style="dotted") >> slack
        alertmgr >> Edge(style="dotted") >> pagerduty

        # Query path.
        grafana >> Edge(label="PromQL (datasource: prometheus)", color="darkgreen") >> prom
