from __future__ import annotations

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country: Mapped[str] = mapped_column(String(64), default="China")
    region: Mapped[str] = mapped_column(String(64))
    province: Mapped[str] = mapped_column(String(64))
    city: Mapped[str] = mapped_column(String(64))
    district: Mapped[str] = mapped_column(String(64))
    site_type: Mapped[str] = mapped_column(String(64))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    climate_risk_index: Mapped[float] = mapped_column(Float, default=0.0)
    congestion_index: Mapped[float] = mapped_column(Float, default=0.0)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    org_type: Mapped[str] = mapped_column(String(64), index=True)
    business_domain: Mapped[str] = mapped_column(String(64))
    tier_level: Mapped[str] = mapped_column(String(16), index=True)
    primary_material_category: Mapped[str] = mapped_column(String(64))
    compliance_score: Mapped[float] = mapped_column(Float, default=90.0)
    esg_score: Mapped[float] = mapped_column(Float, default=80.0)
    single_source_dependency: Mapped[float] = mapped_column(Float, default=0.0)
    geo_risk_index: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    tier_level: Mapped[str] = mapped_column(String(16), index=True)
    facility_type: Mapped[str] = mapped_column(String(64), index=True)
    cold_chain_level: Mapped[str] = mapped_column(String(32))
    capacity_tonnes_per_week: Mapped[float] = mapped_column(Float)
    utilization_rate: Mapped[float] = mapped_column(Float)
    automation_level: Mapped[str] = mapped_column(String(32))
    criticality_index: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    unit: Mapped[str] = mapped_column(String(32), default="kg")
    criticality: Mapped[str] = mapped_column(String(32))
    cold_chain_required: Mapped[bool] = mapped_column(Boolean, default=False)
    base_cost: Mapped[float] = mapped_column(Float)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    shelf_life_days: Mapped[int] = mapped_column(Integer)
    storage_temp_band: Mapped[str] = mapped_column(String(32))
    standard_cost: Mapped[float] = mapped_column(Float)
    unit_price: Mapped[float] = mapped_column(Float)
    target_service_level: Mapped[float] = mapped_column(Float, default=0.98)


class BillOfMaterial(Base):
    __tablename__ = "bill_of_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    quantity_per_unit: Mapped[float] = mapped_column(Float)
    priority_rank: Mapped[int] = mapped_column(Integer, default=1)
    source_tier_hint: Mapped[str] = mapped_column(String(16), default="L1")


class SupplyEdge(Base):
    __tablename__ = "supply_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    edge_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    from_facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    to_facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    material_id: Mapped[int | None] = mapped_column(ForeignKey("materials.id"), nullable=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    tier_level: Mapped[str] = mapped_column(String(16), index=True)
    relation_type: Mapped[str] = mapped_column(String(64), index=True)
    contract_type: Mapped[str] = mapped_column(String(32))
    lead_time_days: Mapped[int] = mapped_column(Integer)
    transit_distance_km: Mapped[float] = mapped_column(Float)
    capacity_tonnes_per_week: Mapped[float] = mapped_column(Float)
    unit_cost: Mapped[float] = mapped_column(Float)
    reliability_score: Mapped[float] = mapped_column(Float)
    carbon_intensity: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class SupplierLot(Base):
    __tablename__ = "supplier_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lot_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    supplier_facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    produced_on: Mapped[Date] = mapped_column(Date)
    harvested_on: Mapped[Date] = mapped_column(Date)
    received_on: Mapped[Date] = mapped_column(Date)
    quantity_kg: Mapped[float] = mapped_column(Float)
    inspection_score: Mapped[float] = mapped_column(Float)
    contamination_risk: Mapped[float] = mapped_column(Float)
    traceability_completeness: Mapped[float] = mapped_column(Float)
    temperature_excursion_minutes: Mapped[int] = mapped_column(Integer, default=0)


class ProductBatch(Base):
    __tablename__ = "product_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    plant_facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    production_date: Mapped[Date] = mapped_column(Date)
    expiry_date: Mapped[Date] = mapped_column(Date)
    planned_qty: Mapped[float] = mapped_column(Float)
    actual_qty: Mapped[float] = mapped_column(Float)
    yield_rate: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="released")
    qr_code: Mapped[str] = mapped_column(String(64), index=True)
    quality_score: Mapped[float] = mapped_column(Float)
    recall_flag: Mapped[bool] = mapped_column(Boolean, default=False)


class BatchComponentUsage(Base):
    __tablename__ = "batch_component_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_batch_id: Mapped[int] = mapped_column(ForeignKey("product_batches.id"), index=True)
    supplier_lot_id: Mapped[int] = mapped_column(ForeignKey("supplier_lots.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), index=True)
    quantity_kg: Mapped[float] = mapped_column(Float)
    upstream_depth_label: Mapped[str] = mapped_column(String(16), default="L1")


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shipment_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    source_facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    destination_facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("product_batches.id"), nullable=True, index=True)
    supplier_lot_id: Mapped[int | None] = mapped_column(ForeignKey("supplier_lots.id"), nullable=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    dispatched_at: Mapped[DateTime] = mapped_column(DateTime)
    arrived_at: Mapped[DateTime] = mapped_column(DateTime)
    planned_hours: Mapped[float] = mapped_column(Float)
    actual_hours: Mapped[float] = mapped_column(Float)
    distance_km: Mapped[float] = mapped_column(Float)
    temp_min_c: Mapped[float] = mapped_column(Float)
    temp_max_c: Mapped[float] = mapped_column(Float)
    cold_chain_breach_minutes: Mapped[int] = mapped_column(Integer, default=0)
    on_time: Mapped[bool] = mapped_column(Boolean, default=True)
    transport_cost: Mapped[float] = mapped_column(Float)
    carrier_name: Mapped[str] = mapped_column(String(128))
    route_risk_score: Mapped[float] = mapped_column(Float)


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(32), index=True)
    item_id: Mapped[int] = mapped_column(Integer, index=True)
    snapshot_date: Mapped[Date] = mapped_column(Date, index=True)
    on_hand_qty: Mapped[float] = mapped_column(Float)
    reserved_qty: Mapped[float] = mapped_column(Float)
    safety_stock_qty: Mapped[float] = mapped_column(Float)
    days_of_cover: Mapped[float] = mapped_column(Float)
    freshness_index: Mapped[float] = mapped_column(Float)


class QualityInspection(Base):
    __tablename__ = "quality_inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    inspected_at: Mapped[DateTime] = mapped_column(DateTime, index=True)
    inspection_stage: Mapped[str] = mapped_column(String(64))
    pathogen_ppm: Mapped[float] = mapped_column(Float)
    residue_ppm: Mapped[float] = mapped_column(Float)
    package_integrity_score: Mapped[float] = mapped_column(Float)
    traceability_completeness: Mapped[float] = mapped_column(Float)
    result: Mapped[str] = mapped_column(String(32))
    notes: Mapped[str] = mapped_column(Text)


class DemandHistory(Base):
    __tablename__ = "demand_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_date: Mapped[Date] = mapped_column(Date, index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(64), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    units_sold: Mapped[float] = mapped_column(Float)
    revenue: Mapped[float] = mapped_column(Float)
    price_index: Mapped[float] = mapped_column(Float)
    promotion_intensity: Mapped[float] = mapped_column(Float)
    weather_index: Mapped[float] = mapped_column(Float)
    festival_index: Mapped[float] = mapped_column(Float)
    waste_units: Mapped[float] = mapped_column(Float)


class ForecastResult(Base):
    __tablename__ = "forecast_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)
    forecast_date: Mapped[Date] = mapped_column(Date, index=True)
    baseline_units: Mapped[float] = mapped_column(Float)
    forecast_units: Mapped[float] = mapped_column(Float)
    lower_bound: Mapped[float] = mapped_column(Float)
    upper_bound: Mapped[float] = mapped_column(Float)
    recommended_safety_stock: Mapped[float] = mapped_column(Float)
    recommended_reorder_point: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(64))
    generated_at: Mapped[DateTime] = mapped_column(DateTime)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_scope: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    entity_code: Mapped[str] = mapped_column(String(64), index=True)
    entity_name: Mapped[str] = mapped_column(String(255))
    tier_level: Mapped[str] = mapped_column(String(16), index=True)
    disruption_probability: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(32), index=True)
    root_causes: Mapped[dict] = mapped_column(JSON)
    recommended_action: Mapped[str] = mapped_column(Text)
    assessed_at: Mapped[DateTime] = mapped_column(DateTime)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"), nullable=True, index=True)
    edge_id: Mapped[int | None] = mapped_column(ForeignKey("supply_edges.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    occurred_at: Mapped[DateTime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    estimated_loss: Mapped[float] = mapped_column(Numeric(14, 2))
    description: Mapped[str] = mapped_column(Text)

