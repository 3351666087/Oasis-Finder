from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

from sqlalchemy import text

from .config import get_settings
from .db import create_app_engine
from .services import (
    get_batch_codes,
    get_batch_trace,
    get_disruptable_facilities,
    get_forecast_series,
    get_product_options,
    get_region_options,
    load_dashboard_snapshot,
    simulate_disruption,
)


MINIMUM_COUNTS = {
    "organizations": 10,
    "facilities": 20,
    "supply_edges": 20,
    "supplier_lots": 20,
    "product_batches": 20,
    "shipments": 20,
    "demand_history": 1000,
}


def _timed_check(name: str, fn) -> dict[str, Any]:
    started = perf_counter()
    try:
        detail = fn()
        return {
            "name": name,
            "status": "pass",
            "elapsed_ms": round((perf_counter() - started) * 1000, 2),
            "detail": detail,
        }
    except Exception as exc:
        return {
            "name": name,
            "status": "fail",
            "elapsed_ms": round((perf_counter() - started) * 1000, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


def _check_database_ping() -> dict[str, Any]:
    engine = create_app_engine()
    with engine.connect() as connection:
        return {"select_1": int(connection.execute(text("SELECT 1")).scalar_one())}


def _check_table_counts() -> dict[str, Any]:
    counts: dict[str, int] = {}
    engine = create_app_engine()
    with engine.connect() as connection:
        for table_name in MINIMUM_COUNTS:
            counts[table_name] = int(connection.execute(text(f"SELECT COUNT(*) FROM `{table_name}`")).scalar_one())

    below_target = {
        table_name: {"actual": actual, "minimum": MINIMUM_COUNTS[table_name]}
        for table_name, actual in counts.items()
        if actual < MINIMUM_COUNTS[table_name]
    }
    if below_target:
        raise RuntimeError(f"Seeded dataset is below expected scale: {below_target}")
    return counts


def _check_dashboard_services() -> dict[str, Any]:
    snapshot = load_dashboard_snapshot()
    return {
        "kpis": snapshot.kpis,
        "risk_rows": int(len(snapshot.risk_distribution)),
        "demand_points": int(len(snapshot.demand_trend)),
        "top_risk_rows": int(len(snapshot.top_risks)),
    }


def _check_traceability_flow() -> dict[str, Any]:
    batch_code = get_batch_codes(1)[0]
    trace = get_batch_trace(batch_code)
    return {
        "batch_code": batch_code,
        "product_name": str(trace["header"]["product_name"]),
        "components": int(len(trace["components"])),
        "shipments": int(len(trace["shipments"])),
    }


def _check_forecast_flow() -> dict[str, Any]:
    sku_code = get_product_options()[0][0]
    region = get_region_options()[0]
    series = get_forecast_series(sku_code, region)
    return {
        "sku_code": sku_code,
        "region": region,
        "history_points": int(len(series["history"])),
        "forecast_points": int(len(series["forecast"])),
    }


def _check_scenario_flow() -> dict[str, Any]:
    best: tuple[str, str, dict[str, Any]] | None = None
    for facility_code, facility_name in get_disruptable_facilities()[:30]:
        result = simulate_disruption(facility_code, 25)
        if int(result["impacted_edges"]) == 0:
            continue
        if best is None or float(result["fill_rate"]) > float(best[2]["fill_rate"]):
            best = (facility_code, facility_name, result)
        if float(result["fill_rate"]) >= 0.999:
            break

    if best is None:
        raise RuntimeError("No disruptable facility is available for scenario validation.")

    facility_code, facility_name, result = best
    return {
        "facility_code": facility_code,
        "facility_name": facility_name,
        "fill_rate": float(result["fill_rate"]),
        "impacted_edges": int(result["impacted_edges"]),
        "plan_rows": int(len(result["alternative_plan"])),
    }


def _check_artifacts() -> dict[str, Any]:
    settings = get_settings()
    required = [
        settings.artifact_root / "risk_metrics.json",
        settings.artifact_root / "forecast_metrics.json",
        settings.artifact_root / "report_assets" / "network_topology.png",
        settings.artifact_root / "ui_captures_native" / "01_dashboard.png",
        settings.artifact_root / "ui_captures_native" / "traceability_bat_00413.png",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing expected evidence artifacts: {missing}")
    return {"required_files": len(required)}


def run_health_check() -> dict[str, Any]:
    checks = [
        _timed_check("database_ping", _check_database_ping),
        _timed_check("table_counts", _check_table_counts),
        _timed_check("dashboard_services", _check_dashboard_services),
        _timed_check("traceability_flow", _check_traceability_flow),
        _timed_check("forecast_flow", _check_forecast_flow),
        _timed_check("scenario_flow", _check_scenario_flow),
        _timed_check("evidence_artifacts", _check_artifacts),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    return {"status": status, "checks": checks}


def format_health_report(payload: dict[str, Any]) -> str:
    lines = [f"Oasis Finder health check: {payload['status'].upper()}"]
    for check in payload["checks"]:
        if check["status"] == "pass":
            detail = json.dumps(check.get("detail", {}), ensure_ascii=False)
            lines.append(f"[PASS] {check['name']} ({check['elapsed_ms']} ms) {detail}")
        else:
            lines.append(f"[FAIL] {check['name']} ({check['elapsed_ms']} ms) {check.get('error', '')}")
    return "\n".join(lines)
