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


def get_facility_node_detail(facility_code: str, max_stage_rows: int = 24) -> dict:
    overview = _read_sql(
        """
        SELECT
            f.id,
            f.facility_code,
            f.name,
            f.tier_level,
            f.facility_type,
            f.cold_chain_level,
            f.capacity_tonnes_per_week,
            f.utilization_rate,
            f.automation_level,
            f.criticality_index,
            l.country,
            l.region,
            l.province,
            l.city,
            l.district,
            l.site_type,
            l.latitude,
            l.longitude,
            l.climate_risk_index,
            l.congestion_index,
            o.org_code,
            o.name AS organization_name,
            o.org_type,
            o.business_domain,
            o.compliance_score,
            o.esg_score,
            o.single_source_dependency,
            COALESCE(r.risk_score, 0) AS risk_score,
            COALESCE(r.risk_level, 'unscored') AS risk_level,
            COALESCE(r.disruption_probability, 0) AS disruption_probability,
            r.recommended_action,
            r.assessed_at,
            (SELECT COUNT(*) FROM supply_edges e WHERE e.to_facility_id = f.id AND e.active = 1) AS inbound_links,
            (SELECT COUNT(*) FROM supply_edges e WHERE e.from_facility_id = f.id AND e.active = 1) AS outbound_links,
            (SELECT COUNT(*) FROM supplier_lots lot WHERE lot.supplier_facility_id = f.id) AS supplier_lots,
            (SELECT COUNT(*) FROM product_batches b WHERE b.plant_facility_id = f.id) AS product_batches,
            (SELECT COUNT(*) FROM shipments s WHERE s.source_facility_id = f.id OR s.destination_facility_id = f.id) AS shipments,
            (SELECT COUNT(*) FROM alert_events a WHERE a.facility_id = f.id AND a.status IN ('open', 'mitigating')) AS active_alerts
        FROM facilities f
        JOIN organizations o ON o.id = f.organization_id
        JOIN locations l ON l.id = f.location_id
        LEFT JOIN risk_assessments r ON r.entity_id = f.id AND r.assessment_scope = 'facility'
        WHERE f.facility_code = :facility_code
        LIMIT 1
        """,
        params={"facility_code": facility_code},
        parse_dates=["assessed_at"],
    )
    if overview.empty:
        raise ValueError(f"Unknown facility: {facility_code}")

    facility_id = int(overview.iloc[0]["id"])
    rows: list[dict] = []

    def add_row(
        stage: str,
        event_time,
        site: str,
        item_or_flow: str,
        evidence_code: str,
        primary_metric: str,
        quality_or_risk: str,
        temperature: str = "",
        traceability: str = "",
        commercial_use: str = "",
    ) -> None:
        rows.append(
            {
                "stage": stage,
                "event_time": event_time,
                "site": site,
                "item_or_flow": item_or_flow,
                "evidence_code": evidence_code,
                "primary_metric": primary_metric,
                "quality_or_risk": quality_or_risk,
                "temperature": temperature,
                "traceability": traceability,
                "commercial_use": commercial_use,
            }
        )

    edge_rows = _read_sql(
        """
        SELECT
            e.edge_code,
            f1.name AS from_name,
            f2.name AS to_name,
            e.tier_level,
            e.relation_type,
            e.lead_time_days,
            e.transit_distance_km,
            e.capacity_tonnes_per_week,
            e.unit_cost,
            e.reliability_score,
            COALESCE(m.name, p.name, e.relation_type) AS flow_name
        FROM supply_edges e
        JOIN facilities f1 ON f1.id = e.from_facility_id
        JOIN facilities f2 ON f2.id = e.to_facility_id
        LEFT JOIN materials m ON m.id = e.material_id
        LEFT JOIN products p ON p.id = e.product_id
        WHERE e.active = 1 AND (e.from_facility_id = :facility_id OR e.to_facility_id = :facility_id)
        ORDER BY e.tier_level, e.reliability_score DESC
        LIMIT 8
        """,
        params={"facility_id": facility_id},
    )
    for _, row in edge_rows.iterrows():
        add_row(
            "Network link",
            None,
            f"{row['from_name']} -> {row['to_name']}",
            str(row["flow_name"]),
            str(row["edge_code"]),
            f"{row['capacity_tonnes_per_week']:.1f} t/week | {row['lead_time_days']} days",
            f"Reliability {row['reliability_score']:.2f} | cost {row['unit_cost']:.2f}",
            "",
            f"Tier {row['tier_level']}",
            "Claims: supplier route, lead time, capacity, reliability",
        )

    lot_rows = _read_sql(
        """
        SELECT
            lot.lot_code,
            m.name AS material_name,
            lot.harvested_on,
            lot.produced_on,
            lot.received_on,
            lot.quantity_kg,
            lot.inspection_score,
            lot.contamination_risk,
            lot.traceability_completeness,
            lot.temperature_excursion_minutes
        FROM supplier_lots lot
        JOIN materials m ON m.id = lot.material_id
        WHERE lot.supplier_facility_id = :facility_id
        ORDER BY lot.received_on DESC
        LIMIT 6
        """,
        params={"facility_id": facility_id},
        parse_dates=["harvested_on", "produced_on", "received_on"],
    )
    for _, row in lot_rows.iterrows():
        add_row(
            "Ingredient lot",
            row["received_on"],
            str(overview.iloc[0]["city"]),
            str(row["material_name"]),
            str(row["lot_code"]),
            f"{row['quantity_kg']:.1f} kg | harvested {row['harvested_on']:%Y-%m-%d}",
            f"Inspection {row['inspection_score']:.1f} | risk {row['contamination_risk']:.2f}",
            f"{int(row['temperature_excursion_minutes'])} min excursion",
            f"{row['traceability_completeness'] * 100:.1f}%",
            "Claims: ingredient source, harvest, receipt, inspection",
        )

    batch_rows = _read_sql(
        """
        SELECT
            b.batch_code,
            p.sku_code,
            p.name AS product_name,
            b.production_date,
            b.expiry_date,
            b.actual_qty,
            b.yield_rate,
            b.quality_score,
            b.status,
            b.qr_code,
            b.recall_flag
        FROM product_batches b
        JOIN products p ON p.id = b.product_id
        WHERE b.plant_facility_id = :facility_id
        ORDER BY b.production_date DESC
        LIMIT 6
        """,
        params={"facility_id": facility_id},
        parse_dates=["production_date", "expiry_date"],
    )
    for _, row in batch_rows.iterrows():
        add_row(
            "Production batch",
            row["production_date"],
            str(overview.iloc[0]["city"]),
            f"{row['sku_code']} | {row['product_name']}",
            str(row["batch_code"]),
            f"{row['actual_qty']:.1f} units | expires {row['expiry_date']:%Y-%m-%d}",
            f"Quality {row['quality_score']:.1f} | yield {row['yield_rate'] * 100:.1f}%",
            "",
            str(row["qr_code"]),
            "Claims: batch date, SKU, expiry, QR evidence",
        )

    shipment_rows = _read_sql(
        """
        SELECT
            s.shipment_code,
            src.name AS source_name,
            dst.name AS destination_name,
            COALESCE(p.name, m.name, 'general flow') AS item_name,
            s.dispatched_at,
            s.arrived_at,
            s.planned_hours,
            s.actual_hours,
            s.distance_km,
            s.temp_min_c,
            s.temp_max_c,
            s.cold_chain_breach_minutes,
            s.on_time,
            s.carrier_name,
            s.route_risk_score
        FROM shipments s
        JOIN facilities src ON src.id = s.source_facility_id
        JOIN facilities dst ON dst.id = s.destination_facility_id
        LEFT JOIN products p ON p.id = s.product_id
        LEFT JOIN supplier_lots lot ON lot.id = s.supplier_lot_id
        LEFT JOIN materials m ON m.id = lot.material_id
        WHERE s.source_facility_id = :facility_id OR s.destination_facility_id = :facility_id
        ORDER BY s.dispatched_at DESC
        LIMIT 8
        """,
        params={"facility_id": facility_id},
        parse_dates=["dispatched_at", "arrived_at"],
    )
    for _, row in shipment_rows.iterrows():
        add_row(
            "Cold-chain shipment",
            row["dispatched_at"],
            f"{row['source_name']} -> {row['destination_name']}",
            str(row["item_name"]),
            str(row["shipment_code"]),
            f"{row['distance_km']:.0f} km | {row['actual_hours']:.1f}/{row['planned_hours']:.1f} h",
            f"On time {bool(row['on_time'])} | route risk {row['route_risk_score']:.1f}",
            f"{row['temp_min_c']:.1f}C to {row['temp_max_c']:.1f}C | breach {int(row['cold_chain_breach_minutes'])} min",
            str(row["carrier_name"]),
            "Claims: dispatch, arrival, temperature, carrier",
        )

    inspection_rows = _read_sql(
        """
        SELECT
            inspected_at,
            inspection_stage,
            entity_type,
            pathogen_ppm,
            residue_ppm,
            package_integrity_score,
            traceability_completeness,
            result,
            notes
        FROM quality_inspections
        WHERE facility_id = :facility_id
        ORDER BY inspected_at DESC
        LIMIT 6
        """,
        params={"facility_id": facility_id},
        parse_dates=["inspected_at"],
    )
    for _, row in inspection_rows.iterrows():
        add_row(
            "Quality checkpoint",
            row["inspected_at"],
            str(overview.iloc[0]["city"]),
            f"{row['entity_type']} | {row['inspection_stage']}",
            str(row["result"]),
            f"pathogen {row['pathogen_ppm']:.3f} ppm | residue {row['residue_ppm']:.3f} ppm",
            f"Package {row['package_integrity_score']:.1f}",
            "",
            f"{row['traceability_completeness'] * 100:.1f}%",
            "Claims: inspection stage, result, trace completeness",
        )

    inventory_rows = _read_sql(
        """
        SELECT
            i.snapshot_date,
            i.item_type,
            COALESCE(p.name, m.name, CONCAT(i.item_type, ' ', i.item_id)) AS item_name,
            i.on_hand_qty,
            i.reserved_qty,
            i.safety_stock_qty,
            i.days_of_cover,
            i.freshness_index
        FROM inventory_snapshots i
        LEFT JOIN products p ON i.item_type = 'product' AND p.id = i.item_id
        LEFT JOIN materials m ON i.item_type = 'material' AND m.id = i.item_id
        WHERE i.facility_id = :facility_id
        ORDER BY i.snapshot_date DESC
        LIMIT 5
        """,
        params={"facility_id": facility_id},
        parse_dates=["snapshot_date"],
    )
    for _, row in inventory_rows.iterrows():
        add_row(
            "Inventory state",
            row["snapshot_date"],
            str(overview.iloc[0]["city"]),
            str(row["item_name"]),
            str(row["item_type"]),
            f"on hand {row['on_hand_qty']:.1f} | reserved {row['reserved_qty']:.1f}",
            f"cover {row['days_of_cover']:.1f} days | freshness {row['freshness_index']:.2f}",
            "",
            f"safety stock {row['safety_stock_qty']:.1f}",
            "Claims: stock level, freshness, availability",
        )

    alert_rows = _read_sql(
        """
        SELECT
            event_code,
            event_type,
            severity,
            occurred_at,
            status,
            estimated_loss,
            description
        FROM alert_events
        WHERE facility_id = :facility_id
        ORDER BY occurred_at DESC
        LIMIT 4
        """,
        params={"facility_id": facility_id},
        parse_dates=["occurred_at"],
    )
    for _, row in alert_rows.iterrows():
        add_row(
            "Risk alert",
            row["occurred_at"],
            str(overview.iloc[0]["city"]),
            str(row["event_type"]),
            str(row["event_code"]),
            f"estimated loss {float(row['estimated_loss']):,.2f}",
            f"{row['severity']} | {row['status']}",
            "",
            str(row["description"]),
            "Claims: event time, status, expected loss",
        )

    stages = pd.DataFrame(rows)
    if not stages.empty:
        stages["_sort_time"] = pd.to_datetime(stages["event_time"], errors="coerce")
        stages = stages.sort_values("_sort_time", ascending=False, na_position="last")
        stages = stages.drop(columns=["_sort_time"]).head(max_stage_rows).reset_index(drop=True)
        stages = stages.rename(
            columns={
                "event_time": "time",
                "item_or_flow": "item",
                "evidence_code": "evidence",
                "primary_metric": "metric",
                "quality_or_risk": "quality_risk",
                "temperature": "temp",
                "traceability": "trace",
                "commercial_use": "claim",
            }
        )

    return {"overview": overview.iloc[0].to_dict(), "stages": stages}


def load_product_shelf() -> pd.DataFrame:
    """Return the consumer-facing SKU shelf shown on the home tab."""
    frame = _read_sql(
        """
        SELECT
            p.id AS product_id,
            p.sku_code,
            p.name AS product_name,
            p.category,
            p.shelf_life_days,
            p.storage_temp_band,
            p.standard_cost,
            p.unit_price,
            ROUND(p.unit_price - p.standard_cost, 2) AS margin_per_unit,
            ROUND((p.unit_price - p.standard_cost) / NULLIF(p.unit_price, 0) * 100, 1) AS margin_rate,
            p.target_service_level,
            b.id AS batch_id,
            b.batch_code AS latest_batch,
            b.production_date,
            b.expiry_date,
            b.actual_qty,
            b.quality_score,
            b.qr_code,
            plant.facility_code AS plant_code,
            plant.name AS plant_name,
            plant_loc.city AS plant_city,
            (SELECT COUNT(*) FROM product_batches b2 WHERE b2.product_id = p.id) AS batch_count,
            (SELECT COUNT(*)
             FROM batch_component_usage u
             WHERE u.product_batch_id = b.id) AS supplier_lot_count,
            (SELECT COUNT(*)
             FROM shipments s
             WHERE s.batch_id = b.id) AS shipment_legs,
            (SELECT ROUND(AVG(CASE WHEN s.on_time THEN 1 ELSE 0 END) * 100, 1)
             FROM shipments s
             WHERE s.batch_id = b.id) AS on_time_rate,
            (SELECT ROUND(AVG(q.traceability_completeness) * 100, 1)
             FROM quality_inspections q
             WHERE q.entity_type = 'product_batch' AND q.entity_id = b.id) AS traceability_score
        FROM products p
        LEFT JOIN product_batches b
          ON b.id = (
              SELECT b0.id
              FROM product_batches b0
              WHERE b0.product_id = p.id
              ORDER BY b0.production_date DESC, b0.id DESC
              LIMIT 1
          )
        LEFT JOIN facilities plant ON plant.id = b.plant_facility_id
        LEFT JOIN locations plant_loc ON plant_loc.id = plant.location_id
        ORDER BY FIELD(p.category, 'protein', 'dairy', 'ready_meal', 'produce'), p.name
        """,
        parse_dates=["production_date", "expiry_date"],
    )
    if frame.empty:
        return frame

    for column in [
        "quality_score",
        "traceability_score",
        "on_time_rate",
        "supplier_lot_count",
        "shipment_legs",
        "margin_rate",
        "batch_count",
    ]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)

    category_labels = {
        "protein": "Protein / chilled meat",
        "dairy": "Dairy / cold chain",
        "ready_meal": "Ready meal",
        "produce": "Fresh produce",
    }
    frame["category_label"] = frame["category"].map(category_labels).fillna(frame["category"])
    frame["proof_score"] = (
        frame["quality_score"] * 0.45
        + frame["traceability_score"] * 0.35
        + frame["on_time_rate"] * 0.20
    ).round(1)
    frame["consumer_claim"] = frame.apply(
        lambda row: (
            f"{int(row['supplier_lot_count'])} lots, {int(row['shipment_legs'])} route legs, "
            f"{row['traceability_score']:.1f}% trace evidence"
        ),
        axis=1,
    )
    return frame[
        [
            "sku_code",
            "product_name",
            "category_label",
            "unit_price",
            "margin_rate",
            "shelf_life_days",
            "storage_temp_band",
            "latest_batch",
            "quality_score",
            "traceability_score",
            "on_time_rate",
            "proof_score",
            "consumer_claim",
            "supplier_lot_count",
            "shipment_legs",
            "plant_name",
            "plant_city",
            "batch_count",
            "product_id",
            "batch_id",
            "production_date",
            "expiry_date",
            "qr_code",
        ]
    ]


def get_product_journey(sku_code: str) -> dict:
    """Build a product-first route, evidence table, and overview for a SKU."""

    def format_date(value) -> str:
        if pd.isna(value):
            return ""
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d")
        return str(value)

    def format_datetime(value) -> str:
        if pd.isna(value):
            return ""
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M")
        return str(value)

    header = _read_sql(
        """
        SELECT
            p.id AS product_id,
            p.sku_code,
            p.name AS product_name,
            p.category,
            p.shelf_life_days,
            p.storage_temp_band,
            p.standard_cost,
            p.unit_price,
            ROUND(p.unit_price - p.standard_cost, 2) AS margin_per_unit,
            ROUND((p.unit_price - p.standard_cost) / NULLIF(p.unit_price, 0) * 100, 1) AS margin_rate,
            p.target_service_level,
            b.id AS batch_id,
            b.batch_code,
            b.production_date,
            b.expiry_date,
            b.actual_qty,
            b.yield_rate,
            b.quality_score,
            b.status,
            b.qr_code,
            b.recall_flag,
            plant.id AS plant_id,
            plant.facility_code AS plant_code,
            plant.name AS plant_name,
            plant.tier_level AS plant_tier,
            plant.facility_type AS plant_type,
            plant_loc.province AS plant_province,
            plant_loc.city AS plant_city,
            plant_loc.district AS plant_district,
            plant_org.name AS plant_operator
        FROM products p
        LEFT JOIN product_batches b
          ON b.id = (
              SELECT b0.id
              FROM product_batches b0
              WHERE b0.product_id = p.id
              ORDER BY b0.production_date DESC, b0.id DESC
              LIMIT 1
          )
        LEFT JOIN facilities plant ON plant.id = b.plant_facility_id
        LEFT JOIN locations plant_loc ON plant_loc.id = plant.location_id
        LEFT JOIN organizations plant_org ON plant_org.id = plant.organization_id
        WHERE p.sku_code = :sku_code
        LIMIT 1
        """,
        params={"sku_code": sku_code},
        parse_dates=["production_date", "expiry_date"],
    )
    if header.empty:
        raise ValueError(f"Unknown product SKU: {sku_code}")

    overview = header.iloc[0].to_dict()
    if pd.isna(overview.get("batch_id")):
        return {
            "overview": overview,
            "route_nodes": pd.DataFrame(),
            "route_edges": pd.DataFrame(),
            "evidence": pd.DataFrame(),
        }

    batch_id = int(overview["batch_id"])
    product_id = int(overview["product_id"])
    plant_code = str(overview["plant_code"])
    plant_city = str(overview["plant_city"])

    components = _read_sql(
        """
        SELECT
            supplier.id AS supplier_id,
            supplier.facility_code AS supplier_code,
            supplier.name AS supplier_name,
            supplier.tier_level AS supplier_tier,
            supplier.facility_type AS supplier_type,
            supplier_loc.province AS supplier_province,
            supplier_loc.city AS supplier_city,
            supplier_org.name AS supplier_operator,
            m.material_code,
            m.name AS material_name,
            m.category AS material_category,
            u.quantity_kg,
            u.upstream_depth_label,
            lot.lot_code,
            lot.harvested_on,
            lot.produced_on,
            lot.received_on,
            lot.inspection_score,
            lot.contamination_risk,
            lot.traceability_completeness,
            lot.temperature_excursion_minutes
        FROM batch_component_usage u
        JOIN supplier_lots lot ON lot.id = u.supplier_lot_id
        JOIN materials m ON m.id = u.material_id
        JOIN facilities supplier ON supplier.id = lot.supplier_facility_id
        JOIN locations supplier_loc ON supplier_loc.id = supplier.location_id
        JOIN organizations supplier_org ON supplier_org.id = supplier.organization_id
        WHERE u.product_batch_id = :batch_id
        ORDER BY u.upstream_depth_label, m.category, m.name
        """,
        params={"batch_id": batch_id},
        parse_dates=["harvested_on", "produced_on", "received_on"],
    )

    shipments = _read_sql(
        """
        SELECT
            s.shipment_code,
            src.id AS source_id,
            src.facility_code AS source_code,
            src.name AS source_name,
            src.tier_level AS source_tier,
            src.facility_type AS source_type,
            src_loc.province AS source_province,
            src_loc.city AS source_city,
            dst.id AS destination_id,
            dst.facility_code AS destination_code,
            dst.name AS destination_name,
            dst.tier_level AS destination_tier,
            dst.facility_type AS destination_type,
            dst_loc.province AS destination_province,
            dst_loc.city AS destination_city,
            s.dispatched_at,
            s.arrived_at,
            s.planned_hours,
            s.actual_hours,
            s.distance_km,
            s.temp_min_c,
            s.temp_max_c,
            s.cold_chain_breach_minutes,
            s.on_time,
            s.transport_cost,
            s.carrier_name,
            s.route_risk_score
        FROM shipments s
        JOIN facilities src ON src.id = s.source_facility_id
        JOIN locations src_loc ON src_loc.id = src.location_id
        JOIN facilities dst ON dst.id = s.destination_facility_id
        JOIN locations dst_loc ON dst_loc.id = dst.location_id
        WHERE s.batch_id = :batch_id
        ORDER BY s.dispatched_at, s.arrived_at
        """,
        params={"batch_id": batch_id},
        parse_dates=["dispatched_at", "arrived_at"],
    )

    inspections = _read_sql(
        """
        SELECT
            q.inspected_at,
            q.inspection_stage,
            q.pathogen_ppm,
            q.residue_ppm,
            q.package_integrity_score,
            q.traceability_completeness,
            q.result,
            q.notes,
            f.name AS facility_name,
            l.city AS facility_city
        FROM quality_inspections q
        JOIN facilities f ON f.id = q.facility_id
        JOIN locations l ON l.id = f.location_id
        WHERE q.entity_type = 'product_batch' AND q.entity_id = :batch_id
        ORDER BY q.inspected_at DESC
        """,
        params={"batch_id": batch_id},
        parse_dates=["inspected_at"],
    )

    inventory = _read_sql(
        """
        SELECT
            i.snapshot_date,
            f.facility_code,
            f.name AS facility_name,
            f.facility_type,
            l.city,
            i.on_hand_qty,
            i.reserved_qty,
            i.safety_stock_qty,
            i.days_of_cover,
            i.freshness_index
        FROM inventory_snapshots i
        JOIN facilities f ON f.id = i.facility_id
        JOIN locations l ON l.id = f.location_id
        WHERE i.item_type = 'product'
          AND i.item_id = :product_id
          AND i.facility_id IN (
              SELECT destination_facility_id
              FROM shipments
              WHERE batch_id = :batch_id
          )
        ORDER BY i.snapshot_date DESC, f.facility_type
        LIMIT 6
        """,
        params={"product_id": product_id, "batch_id": batch_id},
        parse_dates=["snapshot_date"],
    )

    route_node_map: dict[str, dict] = {}
    route_edge_rows: list[dict] = []
    evidence_rows: list[dict] = []

    def upsert_node(
        code: str,
        name: str,
        stage_order: int,
        stage: str,
        tier: str,
        facility_type: str,
        city: str,
        role: str,
        visible_value: str,
    ) -> None:
        if code in route_node_map:
            if visible_value and visible_value not in route_node_map[code]["visible_value"]:
                route_node_map[code]["visible_value"] += f"; {visible_value}"
            return
        route_node_map[code] = {
            "stage_order": stage_order,
            "stage": stage,
            "facility_code": code,
            "facility_name": name,
            "tier": tier,
            "facility_type": facility_type,
            "city": city,
            "role": role,
            "visible_value": visible_value,
        }

    def downstream_stage(facility_type: str, tier: str) -> tuple[int, str, str]:
        if facility_type == "distribution_center":
            return 3, "Distribution center", "Cold-chain distribution"
        if facility_type == "retail_hub":
            return 4, "Retail shelf", "Consumer-facing channel"
        if tier == "CORE":
            return 2, "Processing / packing", "Factory node"
        return 3, "Logistics node", "Route transfer"

    upsert_node(
        plant_code,
        str(overview["plant_name"]),
        2,
        "Processing / packing",
        str(overview["plant_tier"]),
        str(overview["plant_type"]),
        plant_city,
        "Batch owner",
        f"batch {overview['batch_code']} | quality {float(overview['quality_score']):.1f}",
    )

    for _, row in components.iterrows():
        trace_score = float(row["traceability_completeness"]) * 100
        upsert_node(
            str(row["supplier_code"]),
            str(row["supplier_name"]),
            1,
            "Ingredient source",
            str(row["supplier_tier"]),
            str(row["supplier_type"]),
            str(row["supplier_city"]),
            "Supplier lot owner",
            f"{row['material_name']} | lot {row['lot_code']} | inspection {float(row['inspection_score']):.1f}",
        )
        route_edge_rows.append(
            {
                "from_code": row["supplier_code"],
                "to_code": plant_code,
                "flow": row["material_name"],
                "evidence": row["lot_code"],
                "stage": "ingredient_to_plant",
                "metric": f"{float(row['quantity_kg']):.1f} kg | received {format_date(row['received_on'])}",
                "quality_risk": f"inspection {float(row['inspection_score']):.1f} | contamination {float(row['contamination_risk']):.2f}",
                "temperature": f"{int(row['temperature_excursion_minutes'])} min excursion",
                "traceability": f"{trace_score:.1f}%",
            }
        )
        evidence_rows.append(
            {
                "stage": "Ingredient lot",
                "time": row["received_on"],
                "location": f"{row['supplier_city']} -> {plant_city}",
                "item": row["material_name"],
                "evidence": row["lot_code"],
                "metric": f"{float(row['quantity_kg']):.1f} kg | harvested {format_date(row['harvested_on'])}",
                "quality_risk": f"inspection {float(row['inspection_score']):.1f} | risk {float(row['contamination_risk']):.2f}",
                "temp": f"{int(row['temperature_excursion_minutes'])} min excursion",
                "trace": f"{trace_score:.1f}%",
                "consumer_message": "Material source, lot date, and inbound quality evidence are inspectable.",
            }
        )

    evidence_rows.append(
        {
            "stage": "Product identity",
            "time": overview["production_date"],
            "location": f"{overview['plant_name']} | {plant_city}",
            "item": f"{overview['sku_code']} | {overview['product_name']}",
            "evidence": f"{overview['batch_code']} | {overview['qr_code']}",
            "metric": f"{float(overview['actual_qty']):.1f} units | expiry {format_date(overview['expiry_date'])}",
            "quality_risk": f"quality {float(overview['quality_score']):.1f} | yield {float(overview['yield_rate']) * 100:.1f}%",
            "temp": str(overview["storage_temp_band"]),
            "trace": "QR batch proof",
            "consumer_message": "The product card links the SKU to a released batch and QR evidence.",
        }
    )

    for _, row in shipments.iterrows():
        for prefix in ["source", "destination"]:
            order, stage, role = downstream_stage(str(row[f"{prefix}_type"]), str(row[f"{prefix}_tier"]))
            upsert_node(
                str(row[f"{prefix}_code"]),
                str(row[f"{prefix}_name"]),
                order,
                stage,
                str(row[f"{prefix}_tier"]),
                str(row[f"{prefix}_type"]),
                str(row[f"{prefix}_city"]),
                role,
                f"{row['shipment_code']} | {format_datetime(row['arrived_at'])}",
            )
        route_edge_rows.append(
            {
                "from_code": row["source_code"],
                "to_code": row["destination_code"],
                "flow": overview["product_name"],
                "evidence": row["shipment_code"],
                "stage": "product_shipment",
                "metric": f"{float(row['distance_km']):.0f} km | {float(row['actual_hours']):.1f}/{float(row['planned_hours']):.1f} h",
                "quality_risk": f"on time {bool(row['on_time'])} | route risk {float(row['route_risk_score']):.1f}",
                "temperature": f"{float(row['temp_min_c']):.1f}C to {float(row['temp_max_c']):.1f}C | breach {int(row['cold_chain_breach_minutes'])} min",
                "traceability": str(row["carrier_name"]),
            }
        )
        evidence_rows.append(
            {
                "stage": "Cold-chain route",
                "time": row["dispatched_at"],
                "location": f"{row['source_city']} -> {row['destination_city']}",
                "item": overview["product_name"],
                "evidence": row["shipment_code"],
                "metric": f"{float(row['distance_km']):.0f} km | arrived {format_datetime(row['arrived_at'])}",
                "quality_risk": f"on time {bool(row['on_time'])} | route risk {float(row['route_risk_score']):.1f}",
                "temp": f"{float(row['temp_min_c']):.1f}C to {float(row['temp_max_c']):.1f}C | breach {int(row['cold_chain_breach_minutes'])} min",
                "trace": str(row["carrier_name"]),
                "consumer_message": "The route records dispatch time, arrival time, carrier, and cold-chain status.",
            }
        )

    for _, row in inspections.iterrows():
        evidence_rows.append(
            {
                "stage": "Finished-goods QC",
                "time": row["inspected_at"],
                "location": f"{row['facility_name']} | {row['facility_city']}",
                "item": overview["product_name"],
                "evidence": row["result"],
                "metric": f"pathogen {float(row['pathogen_ppm']):.3f} ppm | residue {float(row['residue_ppm']):.3f} ppm",
                "quality_risk": f"package {float(row['package_integrity_score']):.1f}",
                "temp": "",
                "trace": f"{float(row['traceability_completeness']) * 100:.1f}%",
                "consumer_message": "Finished-goods inspection turns the claim into a measurable quality checkpoint.",
            }
        )

    for _, row in inventory.iterrows():
        evidence_rows.append(
            {
                "stage": "Shelf availability",
                "time": row["snapshot_date"],
                "location": f"{row['facility_name']} | {row['city']}",
                "item": overview["product_name"],
                "evidence": row["facility_code"],
                "metric": f"on hand {float(row['on_hand_qty']):.1f} | reserved {float(row['reserved_qty']):.1f}",
                "quality_risk": f"cover {float(row['days_of_cover']):.1f} days | freshness {float(row['freshness_index']):.2f}",
                "temp": str(overview["storage_temp_band"]),
                "trace": f"safety stock {float(row['safety_stock_qty']):.1f}",
                "consumer_message": "Retail availability and freshness make the transparency claim actionable at purchase time.",
            }
        )

    route_nodes = pd.DataFrame(route_node_map.values())
    if not route_nodes.empty:
        route_nodes = route_nodes.sort_values(["stage_order", "facility_name"]).reset_index(drop=True)

    route_edges = pd.DataFrame(route_edge_rows)
    media_slots = pd.DataFrame(
        [
            {
                "slot": "Product photo",
                "interface_key": "merchant_media.product_packshot_url",
                "placeholder": f"merchant_media/{sku_code}/packshot.png",
                "why": "Let shoppers recognize the exact product before reading proof.",
            },
            {
                "slot": "Origin / farm image",
                "interface_key": "merchant_media.origin_image_url",
                "placeholder": f"merchant_media/{sku_code}/origin.jpg",
                "why": "Show where the main ingredient or supplier lot comes from.",
            },
            {
                "slot": "Quality certificate",
                "interface_key": "merchant_media.qc_certificate_url",
                "placeholder": f"merchant_media/{sku_code}/qc_certificate.png",
                "why": "Make the inspection result easy to trust and review.",
            },
            {
                "slot": "Cold-chain proof",
                "interface_key": "merchant_media.temperature_log_url",
                "placeholder": f"merchant_media/{sku_code}/temperature_log.png",
                "why": "Show temperature evidence for delivery and shelf confidence.",
            },
        ]
    )
    evidence = pd.DataFrame(evidence_rows)
    if not evidence.empty:
        evidence["_sort_time"] = pd.to_datetime(evidence["time"], errors="coerce")
        evidence = (
            evidence.sort_values(["_sort_time", "stage"], ascending=[False, True], na_position="last")
            .drop(columns=["_sort_time"])
            .reset_index(drop=True)
        )

    overview["route_node_count"] = int(len(route_nodes))
    overview["route_edge_count"] = int(len(route_edges))
    overview["evidence_row_count"] = int(len(evidence))
    overview["supplier_lot_count"] = int(len(components))
    overview["shipment_leg_count"] = int(len(shipments))
    overview["traceability_score"] = float(
        pd.to_numeric(inspections["traceability_completeness"], errors="coerce").mean() * 100
        if not inspections.empty
        else pd.to_numeric(components["traceability_completeness"], errors="coerce").mean() * 100
    )

    return {
        "overview": overview,
        "route_nodes": route_nodes,
        "route_edges": route_edges,
        "media_slots": media_slots,
        "evidence": evidence,
    }


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
