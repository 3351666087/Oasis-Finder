from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import networkx as nx
from ortools.linear_solver import pywraplp
import pandas as pd
from sqlalchemy import text

from .db import create_app_engine


def _engine():
    return create_app_engine()


def _read_sql(sql: str, params: dict | None = None, parse_dates: list[str] | None = None) -> pd.DataFrame:
    return pd.read_sql(text(sql), _engine(), params=params or {}, parse_dates=parse_dates)


@dataclass
class DashboardSnapshot:
    kpis: dict
    risk_distribution: pd.DataFrame
    demand_trend: pd.DataFrame
    top_risks: pd.DataFrame
    alert_summary: pd.DataFrame


def load_dashboard_snapshot() -> DashboardSnapshot:
    kpi_row = _read_sql(
        """
        SELECT
            (SELECT COUNT(*) FROM facilities WHERE tier_level IN ('L1', 'L2', 'L3')) AS supplier_facilities,
            (SELECT COUNT(*) FROM supply_edges WHERE active = 1) AS active_links,
            (SELECT COUNT(*) FROM product_batches) AS total_batches,
            (SELECT ROUND(AVG(CASE WHEN on_time THEN 1 ELSE 0 END) * 100, 2) FROM shipments) AS on_time_rate,
            (SELECT ROUND(AVG(risk_score), 2) FROM risk_assessments) AS average_risk_score,
            (SELECT COUNT(*) FROM alert_events WHERE status IN ('open', 'mitigating')) AS active_alerts
        """
    ).iloc[0]

    risk_distribution = _read_sql(
        """
        SELECT tier_level, risk_level, COUNT(*) AS entity_count, ROUND(AVG(risk_score), 2) AS avg_score
        FROM risk_assessments
        GROUP BY tier_level, risk_level
        ORDER BY FIELD(tier_level, 'L1', 'L2', 'L3', 'CORE', 'DOWNSTREAM', 'SERVICE'), avg_score DESC
        """
    )

    demand_trend = _read_sql(
        """
        SELECT
            business_date,
            SUM(units_sold) AS units_sold
        FROM demand_history
        WHERE business_date >= CURDATE() - INTERVAL 60 DAY
        GROUP BY business_date
        ORDER BY business_date
        """,
        parse_dates=["business_date"],
    )

    top_risks = _read_sql(
        """
        SELECT
            r.entity_code,
            r.entity_name,
            r.tier_level,
            r.risk_score,
            r.risk_level,
            r.disruption_probability,
            r.recommended_action
        FROM risk_assessments r
        ORDER BY r.risk_score DESC
        LIMIT 12
        """
    )

    alert_summary = _read_sql(
        """
        SELECT severity, COUNT(*) AS alert_count, ROUND(SUM(estimated_loss), 2) AS estimated_loss
        FROM alert_events
        GROUP BY severity
        ORDER BY FIELD(severity, 'critical', 'high', 'medium', 'low')
        """
    )

    return DashboardSnapshot(
        kpis={
            "supplier_facilities": int(kpi_row["supplier_facilities"]),
            "active_links": int(kpi_row["active_links"]),
            "total_batches": int(kpi_row["total_batches"]),
            "on_time_rate": float(kpi_row["on_time_rate"] or 0.0),
            "average_risk_score": float(kpi_row["average_risk_score"] or 0.0),
            "active_alerts": int(kpi_row["active_alerts"]),
        },
        risk_distribution=risk_distribution,
        demand_trend=demand_trend,
        top_risks=top_risks,
        alert_summary=alert_summary,
    )


def load_network_data(tier_filter: str = "ALL") -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = _read_sql(
        """
        SELECT
            f.id,
            f.facility_code,
            f.name,
            f.tier_level,
            f.facility_type,
            f.capacity_tonnes_per_week,
            f.utilization_rate,
            l.region,
            l.city,
            o.name AS organization_name,
            COALESCE(r.risk_score, 0) AS risk_score
        FROM facilities f
        JOIN organizations o ON o.id = f.organization_id
        JOIN locations l ON l.id = f.location_id
        LEFT JOIN risk_assessments r ON r.entity_id = f.id AND r.assessment_scope = 'facility'
        ORDER BY FIELD(f.tier_level, 'L1', 'L2', 'L3', 'CORE', 'DOWNSTREAM', 'SERVICE'), f.name
        """
    )
    edges = _read_sql(
        """
        SELECT
            e.id,
            e.edge_code,
            e.from_facility_id,
            f1.facility_code AS from_code,
            f1.name AS from_name,
            e.to_facility_id,
            f2.facility_code AS to_code,
            f2.name AS to_name,
            e.tier_level,
            e.relation_type,
            e.lead_time_days,
            e.transit_distance_km,
            e.capacity_tonnes_per_week,
            e.unit_cost,
            e.reliability_score,
            m.name AS material_name,
            p.name AS product_name
        FROM supply_edges e
        JOIN facilities f1 ON f1.id = e.from_facility_id
        JOIN facilities f2 ON f2.id = e.to_facility_id
        LEFT JOIN materials m ON m.id = e.material_id
        LEFT JOIN products p ON p.id = e.product_id
        WHERE e.active = 1
        """
    )

    if tier_filter != "ALL":
        keep_nodes = nodes[nodes["tier_level"] == tier_filter]["id"].tolist()
        nodes = nodes[nodes["tier_level"] == tier_filter].copy()
        edges = edges[(edges["from_facility_id"].isin(keep_nodes)) | (edges["to_facility_id"].isin(keep_nodes))].copy()

    return nodes, edges


def get_batch_codes(limit: int = 200) -> list[str]:
    frame = _read_sql(
        f"""
        SELECT batch_code
        FROM product_batches
        ORDER BY production_date DESC
        LIMIT {limit}
        """
    )
    return frame["batch_code"].tolist()


def get_batch_trace(batch_code: str) -> dict:
    header = _read_sql(
        """
        SELECT
            b.id AS batch_id,
            b.batch_code,
            p.sku_code,
            p.name AS product_name,
            b.production_date,
            b.expiry_date,
            b.actual_qty,
            b.quality_score,
            plant.name AS plant_name
        FROM product_batches b
        JOIN products p ON p.id = b.product_id
        JOIN facilities plant ON plant.id = b.plant_facility_id
        WHERE b.batch_code = :batch_code
        """,
        params={"batch_code": batch_code},
        parse_dates=["production_date", "expiry_date"],
    )
    if header.empty:
        raise ValueError(f"Unknown batch code: {batch_code}")

    batch_id = int(header.iloc[0]["batch_id"])
    components = _read_sql(
        """
        SELECT
            m.name AS material_name,
            u.quantity_kg,
            u.upstream_depth_label,
            lot.lot_code,
            supplier.facility_code AS supplier_code,
            supplier.name AS supplier_facility,
            org.name AS supplier_org,
            lot.inspection_score,
            lot.traceability_completeness
        FROM batch_component_usage u
        JOIN supplier_lots lot ON lot.id = u.supplier_lot_id
        JOIN materials m ON m.id = u.material_id
        JOIN facilities supplier ON supplier.id = lot.supplier_facility_id
        JOIN organizations org ON org.id = supplier.organization_id
        WHERE u.product_batch_id = :batch_id
        ORDER BY m.name
        """,
        params={"batch_id": batch_id},
    )
    shipments = _read_sql(
        """
        SELECT
            shipment_code,
            src.name AS source_name,
            dst.name AS destination_name,
            dispatched_at,
            arrived_at,
            planned_hours,
            actual_hours,
            on_time,
            cold_chain_breach_minutes,
            carrier_name
        FROM shipments s
        JOIN facilities src ON src.id = s.source_facility_id
        JOIN facilities dst ON dst.id = s.destination_facility_id
        WHERE s.batch_id = :batch_id
        ORDER BY s.dispatched_at
        """,
        params={"batch_id": batch_id},
        parse_dates=["dispatched_at", "arrived_at"],
    )

    return {
        "header": header.iloc[0].to_dict(),
        "components": components,
        "shipments": shipments,
    }


def get_forecast_series(sku_code: str, region: str) -> dict:
    history = _read_sql(
        """
        SELECT
            d.business_date,
            SUM(d.units_sold) AS units_sold
        FROM demand_history d
        JOIN products p ON p.id = d.product_id
        WHERE p.sku_code = :sku_code AND d.region = :region
        GROUP BY d.business_date
        ORDER BY d.business_date
        """,
        params={"sku_code": sku_code, "region": region},
        parse_dates=["business_date"],
    )
    forecast = _read_sql(
        """
        SELECT
            f.forecast_date,
            f.baseline_units,
            f.forecast_units,
            f.lower_bound,
            f.upper_bound,
            f.recommended_safety_stock,
            f.recommended_reorder_point
        FROM forecast_results f
        JOIN products p ON p.id = f.product_id
        WHERE p.sku_code = :sku_code AND f.region = :region
        ORDER BY f.forecast_date
        """,
        params={"sku_code": sku_code, "region": region},
        parse_dates=["forecast_date"],
    )
    return {"history": history.tail(90), "forecast": forecast}


def get_product_options() -> list[tuple[str, str]]:
    frame = _read_sql("SELECT sku_code, name FROM products ORDER BY sku_code")
    return [(row["sku_code"], row["name"]) for _, row in frame.iterrows()]


def get_region_options() -> list[str]:
    frame = _read_sql("SELECT DISTINCT region FROM demand_history ORDER BY region")
    return frame["region"].tolist()


def get_disruptable_facilities() -> list[tuple[str, str]]:
    frame = _read_sql(
        """
        SELECT facility_code, name
        FROM facilities
        WHERE tier_level IN ('L1', 'L2', 'L3', 'CORE')
        ORDER BY FIELD(tier_level, 'L1', 'L2', 'L3', 'CORE'), name
        """
    )
    return [(row["facility_code"], row["name"]) for _, row in frame.iterrows()]


def simulate_disruption(facility_code: str, capacity_drop_pct: float) -> dict:
    nodes, edges = load_network_data("ALL")
    risk = _read_sql("SELECT entity_id, risk_score FROM risk_assessments WHERE assessment_scope = 'facility'")
    risk_map = dict(zip(risk["entity_id"], risk["risk_score"]))

    selected = nodes[nodes["facility_code"] == facility_code]
    if selected.empty:
        raise ValueError(f"Unknown facility: {facility_code}")
    facility_row = selected.iloc[0]
    selected_id = int(facility_row["id"])
    outgoing = edges[edges["from_facility_id"] == selected_id].copy()
    reduction_ratio = max(0.0, min(1.0, capacity_drop_pct / 100))

    if outgoing.empty:
        return {
            "facility_name": facility_row["name"],
            "fill_rate": 1.0,
            "impacted_edges": 0,
            "impacted_batches": 0,
            "alternative_plan": pd.DataFrame(columns=["destination", "replacement", "flow_label", "allocated_tonnes", "estimated_cost", "risk_score"]),
            "message": "Selected facility has no outgoing flow edges to simulate.",
        }

    solver = pywraplp.Solver.CreateSolver("GLOP")
    alternatives = []
    total_demand = 0.0
    unmet_penalty_terms = []
    objective = solver.Objective()
    objective.SetMinimization()

    for _, disrupted in outgoing.iterrows():
        required = float(disrupted["capacity_tonnes_per_week"]) * reduction_ratio
        total_demand += required
        flow_label = disrupted["material_name"] or disrupted["product_name"] or disrupted["relation_type"]
        unmet = solver.NumVar(0, required, f"unmet_{int(disrupted['id'])}")
        unmet_penalty_terms.append(unmet)
        objective.SetCoefficient(unmet, 1000.0)

        if pd.notna(disrupted["material_name"]):
            candidate_pool = edges[
                (edges["to_facility_id"] == disrupted["to_facility_id"])
                & (edges["id"] != disrupted["id"])
                & (edges["material_name"] == disrupted["material_name"])
            ]
        else:
            candidate_pool = edges[
                (edges["to_facility_id"] == disrupted["to_facility_id"])
                & (edges["id"] != disrupted["id"])
                & (edges["product_name"] == disrupted["product_name"])
            ]

        flow_vars = []
        for _, candidate in candidate_pool.iterrows():
            candidate_id = int(candidate["from_facility_id"])
            candidate_risk = float(risk_map.get(candidate_id, 30.0))
            spare_capacity = float(candidate["capacity_tonnes_per_week"]) * max(0.12, 0.55 - nodes.set_index("id").loc[candidate_id, "utilization_rate"])
            var = solver.NumVar(0, max(0.0, spare_capacity), f"alloc_{int(disrupted['id'])}_{candidate_id}")
            weighted_cost = float(candidate["unit_cost"]) * (1 + candidate_risk / 120)
            objective.SetCoefficient(var, weighted_cost)
            flow_vars.append((var, candidate, candidate_risk))

        coverage = solver.Constraint(required, required)
        coverage.SetCoefficient(unmet, 1)
        for var, _, _ in flow_vars:
            coverage.SetCoefficient(var, 1)

        alternatives.append((disrupted, flow_vars))

    status = solver.Solve()
    plan_rows = []
    total_unmet = 0.0
    for disrupted, flow_vars in alternatives:
        flow_label = disrupted["material_name"] or disrupted["product_name"] or disrupted["relation_type"]
        for var, candidate, candidate_risk in flow_vars:
            value = var.solution_value() if status == pywraplp.Solver.OPTIMAL else 0.0
            if value <= 0.01:
                continue
            plan_rows.append(
                {
                    "destination": candidate["to_name"],
                    "replacement": candidate["from_name"],
                    "flow_label": flow_label,
                    "allocated_tonnes": round(value, 2),
                    "estimated_cost": round(value * float(candidate["unit_cost"]), 2),
                    "risk_score": round(candidate_risk, 2),
                }
            )

    for unmet in unmet_penalty_terms:
        total_unmet += unmet.solution_value() if status == pywraplp.Solver.OPTIMAL else 0.0

    fill_rate = 1.0 if total_demand == 0 else max(0.0, 1 - total_unmet / total_demand)
    impacted_batches = _read_sql(
        """
        SELECT COUNT(DISTINCT batch_id) AS impacted_batches
        FROM shipments
        WHERE batch_id IS NOT NULL
          AND source_facility_id = (
            SELECT id FROM facilities WHERE facility_code = :facility_code
          )
          AND dispatched_at >= NOW() - INTERVAL 14 DAY
        """,
        params={"facility_code": facility_code},
    ).iloc[0]["impacted_batches"]

    return {
        "facility_name": facility_row["name"],
        "fill_rate": round(fill_rate, 4),
        "impacted_edges": int(len(outgoing)),
        "impacted_batches": int(impacted_batches or 0),
        "alternative_plan": pd.DataFrame(plan_rows).sort_values(["risk_score", "estimated_cost"]) if plan_rows else pd.DataFrame(columns=["destination", "replacement", "flow_label", "allocated_tonnes", "estimated_cost", "risk_score"]),
        "message": f"Scenario completed with {round(fill_rate * 100, 1)}% projected recovery coverage.",
    }


def build_network_graph() -> nx.DiGraph:
    nodes, edges = load_network_data()
    graph = nx.DiGraph()
    for _, node in nodes.iterrows():
        graph.add_node(
            node["facility_code"],
            label=node["name"],
            tier=node["tier_level"],
            risk=float(node["risk_score"]),
            region=node["region"],
        )
    for _, edge in edges.iterrows():
        graph.add_edge(
            edge["from_code"],
            edge["to_code"],
            label=edge["material_name"] or edge["product_name"] or edge["relation_type"],
            tier=edge["tier_level"],
            weight=float(edge["unit_cost"]),
        )
    return graph

