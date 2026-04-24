from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import math
import random

from faker import Faker
import numpy as np
from sqlalchemy import delete

from .db import session_scope
from .models import (
    AlertEvent,
    BatchComponentUsage,
    BillOfMaterial,
    DemandHistory,
    Facility,
    ForecastResult,
    InventorySnapshot,
    Location,
    Material,
    Organization,
    Product,
    ProductBatch,
    QualityInspection,
    RiskAssessment,
    Shipment,
    SupplierLot,
    SupplyEdge,
)

RANDOM_SEED = 20260327
fake = Faker("en_US")


@dataclass(frozen=True)
class GeoSeed:
    region: str
    province: str
    city: str
    district: str
    latitude: float
    longitude: float
    climate_risk_index: float
    congestion_index: float


LOCATION_SEEDS = [
    GeoSeed("North China", "Beijing", "Beijing", "Daxing", 39.7269, 116.3414, 0.26, 0.70),
    GeoSeed("North China", "Tianjin", "Tianjin", "Binhai", 39.0324, 117.6981, 0.31, 0.76),
    GeoSeed("North China", "Shandong", "Jinan", "Licheng", 36.6512, 117.1201, 0.28, 0.54),
    GeoSeed("North China", "Shandong", "Qingdao", "Huangdao", 35.9606, 120.1981, 0.23, 0.67),
    GeoSeed("East China", "Shanghai", "Shanghai", "Pudong", 31.2304, 121.4737, 0.22, 0.81),
    GeoSeed("East China", "Jiangsu", "Suzhou", "Wujiang", 31.2990, 120.5853, 0.24, 0.58),
    GeoSeed("East China", "Zhejiang", "Hangzhou", "Yuhang", 30.2741, 120.1551, 0.27, 0.60),
    GeoSeed("East China", "Zhejiang", "Ningbo", "Beilun", 29.8683, 121.5440, 0.25, 0.72),
    GeoSeed("Central China", "Henan", "Zhengzhou", "Xinzheng", 34.7473, 113.6254, 0.35, 0.52),
    GeoSeed("Central China", "Hubei", "Wuhan", "Dongxihu", 30.5928, 114.3055, 0.43, 0.63),
    GeoSeed("Central China", "Hunan", "Changsha", "Yuelu", 28.2282, 112.9388, 0.41, 0.49),
    GeoSeed("South China", "Guangdong", "Guangzhou", "Nansha", 23.1291, 113.2644, 0.47, 0.75),
    GeoSeed("South China", "Guangdong", "Shenzhen", "Longgang", 22.5431, 114.0579, 0.39, 0.83),
    GeoSeed("South China", "Fujian", "Fuzhou", "Minhou", 26.0745, 119.2965, 0.38, 0.56),
    GeoSeed("South China", "Fujian", "Xiamen", "Haicang", 24.4798, 118.0894, 0.31, 0.62),
    GeoSeed("West China", "Sichuan", "Chengdu", "Shuangliu", 30.5728, 104.0668, 0.36, 0.51),
    GeoSeed("West China", "Chongqing", "Chongqing", "Jiangbei", 29.5630, 106.5516, 0.44, 0.65),
    GeoSeed("West China", "Shaanxi", "Xi'an", "Gaoling", 34.3416, 108.9398, 0.33, 0.48),
    GeoSeed("Southwest", "Yunnan", "Kunming", "Guandu", 25.0389, 102.7183, 0.29, 0.35),
    GeoSeed("Northeast China", "Heilongjiang", "Harbin", "Shuangcheng", 45.8038, 126.5350, 0.51, 0.34),
    GeoSeed("Northeast China", "Jilin", "Changchun", "Kuancheng", 43.8171, 125.3235, 0.46, 0.29),
    GeoSeed("Northeast China", "Liaoning", "Shenyang", "Tiexi", 41.8057, 123.4315, 0.42, 0.45),
]

MATERIAL_SEEDS = [
    ("MAT-BROILER", "Broiler Protein Input", "broiler_input", "kg", "critical", True, 8.8),
    ("MAT-PORK", "Pork Protein Input", "pork_input", "kg", "critical", True, 11.5),
    ("MAT-TOMATO", "Tomato Raw Material", "tomato_raw", "kg", "high", True, 3.4),
    ("MAT-GREENS", "Leafy Green Raw Material", "leafy_green_raw", "kg", "high", True, 2.7),
    ("MAT-MILK", "Raw Milk", "raw_milk", "kg", "critical", True, 4.2),
    ("MAT-SEASON", "Seasoning Blend", "seasoning_blend", "kg", "medium", False, 6.5),
    ("MAT-FILM", "PE Packaging Film", "pe_film", "kg", "high", False, 9.1),
    ("MAT-CARTON", "Corrugated Carton", "corrugated_carton", "kg", "high", False, 5.4),
    ("MAT-LABEL", "QR Traceability Label", "qr_label", "unit", "high", False, 0.22),
    ("MAT-GEL", "Cold Chain Gel Pack", "gel_pack", "unit", "medium", True, 1.25),
    ("MAT-BOTTLE", "PET Bottle", "pet_bottle", "unit", "medium", False, 0.55),
    ("MAT-CULTURE", "Starter Culture", "starter_culture", "kg", "medium", True, 12.0),
]

PRODUCT_SEEDS = [
    ("SKU-CHB-500", "Chilled Chicken Breast 500g", "protein", 7, "0C to 4C", 11.4, 24.9),
    ("SKU-CHW-1000", "Chilled Chicken Wings 1kg", "protein", 7, "0C to 4C", 19.6, 41.9),
    ("SKU-PKL-500", "Premium Pork Loin 500g", "protein", 6, "0C to 4C", 15.9, 34.8),
    ("SKU-PKR-800", "Premium Pork Ribs 800g", "protein", 6, "0C to 4C", 24.4, 52.0),
    ("SKU-TOM-1000", "Fresh Tomato Pack 1kg", "produce", 5, "2C to 8C", 4.6, 11.8),
    ("SKU-VEG-600", "Leafy Greens Mix 600g", "produce", 4, "2C to 8C", 3.9, 9.9),
    ("SKU-DUM-450", "Fresh Chicken Dumpling 450g", "ready_meal", 9, "-5C to 2C", 8.5, 18.6),
    ("SKU-MLK-950", "Pasteurised Milk 950ml", "dairy", 8, "0C to 4C", 6.1, 13.2),
]

BOM_MAP = {
    "SKU-CHB-500": [("MAT-BROILER", 0.48), ("MAT-FILM", 0.01), ("MAT-CARTON", 0.04), ("MAT-LABEL", 1), ("MAT-GEL", 1)],
    "SKU-CHW-1000": [("MAT-BROILER", 0.96), ("MAT-FILM", 0.02), ("MAT-CARTON", 0.06), ("MAT-LABEL", 1), ("MAT-GEL", 1)],
    "SKU-PKL-500": [("MAT-PORK", 0.49), ("MAT-FILM", 0.01), ("MAT-CARTON", 0.04), ("MAT-LABEL", 1), ("MAT-GEL", 1)],
    "SKU-PKR-800": [("MAT-PORK", 0.78), ("MAT-FILM", 0.02), ("MAT-CARTON", 0.05), ("MAT-LABEL", 1), ("MAT-GEL", 1)],
    "SKU-TOM-1000": [("MAT-TOMATO", 0.98), ("MAT-FILM", 0.01), ("MAT-CARTON", 0.04), ("MAT-LABEL", 1)],
    "SKU-VEG-600": [("MAT-GREENS", 0.57), ("MAT-FILM", 0.01), ("MAT-CARTON", 0.03), ("MAT-LABEL", 1)],
    "SKU-DUM-450": [("MAT-BROILER", 0.22), ("MAT-SEASON", 0.05), ("MAT-FILM", 0.01), ("MAT-CARTON", 0.03), ("MAT-LABEL", 1), ("MAT-GEL", 1)],
    "SKU-MLK-950": [("MAT-MILK", 0.93), ("MAT-BOTTLE", 1), ("MAT-LABEL", 1), ("MAT-CULTURE", 0.01)],
}

PLANT_PORTFOLIO = {
    "FAC-PLANT-SHA": ["SKU-CHB-500", "SKU-CHW-1000", "SKU-DUM-450"],
    "FAC-PLANT-WUH": ["SKU-PKL-500", "SKU-PKR-800", "SKU-DUM-450"],
    "FAC-PLANT-GUA": ["SKU-TOM-1000", "SKU-VEG-600", "SKU-MLK-950"],
    "FAC-PLANT-CDU": ["SKU-CHB-500", "SKU-PKL-500", "SKU-TOM-1000", "SKU-MLK-950"],
}

L1_BLUEPRINTS = [
    ("broiler_input", "poultry_integrator", "processing_hub", 4),
    ("pork_input", "swine_integrator", "processing_hub", 4),
    ("tomato_raw", "produce_cooperative", "fresh_pack_hub", 2),
    ("leafy_green_raw", "produce_cooperative", "fresh_pack_hub", 2),
    ("raw_milk", "dairy_collective", "cold_milk_hub", 2),
    ("seasoning_blend", "food_ingredient_supplier", "ingredient_plant", 1),
    ("pe_film", "packaging_supplier", "packaging_plant", 2),
    ("corrugated_carton", "packaging_supplier", "carton_factory", 2),
    ("qr_label", "digital_label_supplier", "print_hub", 1),
    ("gel_pack", "cold_chain_supplier", "cold_chain_material_hub", 1),
    ("pet_bottle", "bottle_supplier", "bottle_factory", 1),
    ("starter_culture", "bio_ingredient_supplier", "bio_ingredient_lab", 1),
]

L2_BLUEPRINTS = [
    ("feed_premix", "feed_processor", "feed_mill", 4),
    ("vet_pharma", "veterinary_supplier", "pharma_plant", 2),
    ("polymer_resin", "chemical_processor", "polymer_plant", 2),
    ("paper_pulp", "material_processor", "pulp_mill", 2),
    ("cold_storage_service", "cold_chain_service", "cold_storage_hub", 2),
    ("ink_additive", "specialty_chemical_supplier", "chemical_hub", 1),
    ("bottle_preform", "packaging_component_supplier", "preform_plant", 1),
    ("spice_base", "food_ingredient_supplier", "ingredient_hub", 1),
    ("dairy_enzyme", "bio_ingredient_supplier", "biotech_plant", 1),
    ("seedling_service", "agri_input_supplier", "nursery_hub", 2),
    ("label_substrate", "material_processor", "label_substrate_plant", 1),
    ("refrigerant", "cold_chain_supplier", "industrial_gas_hub", 1),
]

L3_BLUEPRINTS = [
    ("corn_source", "farm_cluster", "grain_origin", 4),
    ("soybean_source", "farm_cluster", "grain_origin", 4),
    ("crude_resin", "petrochemical_source", "petrochemical_terminal", 3),
    ("recycled_fiber", "resource_recycler", "fiber_yard", 3),
    ("natural_gas", "energy_supplier", "energy_terminal", 2),
    ("aluminium_foil", "metal_processor", "metal_hub", 2),
    ("raw_spice", "agri_source", "spice_origin", 2),
    ("whey_source", "dairy_upstream", "dairy_origin", 2),
    ("industrial_salt", "chemical_source", "salt_source", 2),
    ("printing_resin", "chemical_source", "resin_hub", 2),
    ("seed_origin", "agri_source", "seed_origin", 3),
    ("co2_source", "industrial_gas_source", "gas_source", 1),
]

L2_TO_L1_SUPPORT = {
    "broiler_input": ["feed_premix", "vet_pharma", "cold_storage_service"],
    "pork_input": ["feed_premix", "vet_pharma", "cold_storage_service"],
    "tomato_raw": ["seedling_service", "cold_storage_service"],
    "leafy_green_raw": ["seedling_service", "cold_storage_service"],
    "raw_milk": ["feed_premix", "dairy_enzyme", "cold_storage_service"],
    "seasoning_blend": ["spice_base"],
    "pe_film": ["polymer_resin"],
    "corrugated_carton": ["paper_pulp"],
    "qr_label": ["label_substrate", "ink_additive"],
    "gel_pack": ["refrigerant"],
    "pet_bottle": ["bottle_preform", "polymer_resin"],
    "starter_culture": ["dairy_enzyme"],
}

L3_TO_L2_SUPPORT = {
    "feed_premix": ["corn_source", "soybean_source"],
    "vet_pharma": ["industrial_salt", "natural_gas"],
    "polymer_resin": ["crude_resin", "natural_gas"],
    "paper_pulp": ["recycled_fiber", "natural_gas"],
    "cold_storage_service": ["natural_gas", "co2_source"],
    "ink_additive": ["printing_resin", "industrial_salt"],
    "bottle_preform": ["crude_resin", "aluminium_foil"],
    "spice_base": ["raw_spice"],
    "dairy_enzyme": ["whey_source"],
    "seedling_service": ["seed_origin"],
    "label_substrate": ["recycled_fiber", "printing_resin"],
    "refrigerant": ["co2_source", "natural_gas"],
}

REGIONS = ["North China", "East China", "South China", "Central China", "West China", "Northeast China"]
CHANNELS = ["Modern Trade", "E-Commerce"]
origin_location_lookup: dict[int, Location] = {}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def combine_dt(target_date: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(target_date, time(hour=hour, minute=minute))


def purge_existing_data(session) -> None:
    for model in [
        ForecastResult,
        RiskAssessment,
        AlertEvent,
        InventorySnapshot,
        QualityInspection,
        Shipment,
        BatchComponentUsage,
        ProductBatch,
        SupplierLot,
        SupplyEdge,
        BillOfMaterial,
        Product,
        Material,
        Facility,
        Organization,
        Location,
    ]:
        session.execute(delete(model))
    session.flush()


def pick_location(rng: random.Random, locations: dict[str, list[Location]], preferred_regions: list[str] | None = None) -> Location:
    pool = []
    if preferred_regions:
        for region in preferred_regions:
            pool.extend(locations[region])
    return rng.choice(pool or [item for items in locations.values() for item in items])


def create_supply_edge(
    code: str,
    origin: Facility,
    destination: Facility,
    material_id: int | None,
    product_id: int | None,
    tier_level: str,
    relation_type: str,
    rng: random.Random,
) -> SupplyEdge:
    origin_location = origin_location_lookup[origin.location_id]
    destination_location = origin_location_lookup[destination.location_id]
    distance = haversine_km(
        origin_location.latitude,
        origin_location.longitude,
        destination_location.latitude,
        destination_location.longitude,
    )
    reliability = max(72.0, 98.5 - distance / 50 - rng.random() * 6.0)
    return SupplyEdge(
        edge_code=code,
        from_facility_id=origin.id,
        to_facility_id=destination.id,
        material_id=material_id,
        product_id=product_id,
        tier_level=tier_level,
        relation_type=relation_type,
        contract_type=rng.choice(["annual_frame", "strategic_reserve", "spot_plus_buffer"]),
        lead_time_days=max(1, int(distance / 280) + rng.randint(1, 4)),
        transit_distance_km=round(distance, 1),
        capacity_tonnes_per_week=round(rng.uniform(30, 220), 1),
        unit_cost=round(rng.uniform(1.2, 14.5), 2),
        reliability_score=round(reliability, 2),
        carbon_intensity=round(rng.uniform(0.4, 3.5), 2),
        active=True,
    )


def seed_database() -> None:
    rng = random.Random(RANDOM_SEED)
    np_rng = np.random.default_rng(RANDOM_SEED)
    fake.seed_instance(RANDOM_SEED)
    today = date.today()

    with session_scope() as session:
        purge_existing_data(session)

        location_objects = [
            Location(
                country="China",
                region=seed.region,
                province=seed.province,
                city=seed.city,
                district=seed.district,
                site_type="regional_hub",
                latitude=seed.latitude,
                longitude=seed.longitude,
                climate_risk_index=seed.climate_risk_index,
                congestion_index=seed.congestion_index,
            )
            for seed in LOCATION_SEEDS
        ]
        session.add_all(location_objects)
        session.flush()

        locations_by_region: dict[str, list[Location]] = defaultdict(list)
        for location in location_objects:
            locations_by_region[location.region].append(location)
            origin_location_lookup[location.id] = location

        organizations: list[Organization] = []
        facilities: list[Facility] = []

        focal_org = Organization(
            org_code="ORG-CP-001",
            name="CP Fresh Mesh Control Tower",
            org_type="focal_enterprise",
            business_domain="fresh_food",
            tier_level="CORE",
            primary_material_category="multi-category",
            compliance_score=97.5,
            esg_score=89.2,
            single_source_dependency=0.21,
            geo_risk_index=0.18,
            active=True,
        )
        session.add(focal_org)
        session.flush()
        organizations.append(focal_org)

        core_facility_specs = [
            ("FAC-PLANT-SHA", "Shanghai Integrated Protein Plant", "plant", "CORE", "gold", 340, 0.78, "high", 0.92, "East China", "Shanghai"),
            ("FAC-PLANT-WUH", "Wuhan Smart Protein Plant", "plant", "CORE", "gold", 310, 0.81, "high", 0.91, "Central China", "Wuhan"),
            ("FAC-PLANT-GUA", "Guangzhou Fresh Produce Plant", "plant", "CORE", "platinum", 280, 0.74, "medium", 0.88, "South China", "Guangzhou"),
            ("FAC-PLANT-CDU", "Chengdu Resilience Food Plant", "plant", "CORE", "gold", 260, 0.76, "high", 0.90, "West China", "Chengdu"),
            ("FAC-DC-SHA", "Shanghai National Distribution Center", "distribution_center", "CORE", "platinum", 420, 0.73, "medium", 0.85, "East China", "Shanghai"),
            ("FAC-DC-WUH", "Wuhan Central Distribution Center", "distribution_center", "CORE", "gold", 380, 0.71, "medium", 0.84, "Central China", "Wuhan"),
            ("FAC-DC-GUA", "Guangzhou Southern Distribution Center", "distribution_center", "CORE", "gold", 400, 0.77, "medium", 0.86, "South China", "Guangzhou"),
            ("FAC-DC-BEI", "Beijing Northern Distribution Center", "distribution_center", "CORE", "gold", 360, 0.72, "medium", 0.84, "North China", "Beijing"),
            ("FAC-DC-HRB", "Harbin Northeast Distribution Center", "distribution_center", "CORE", "silver", 220, 0.65, "medium", 0.75, "Northeast China", "Harbin"),
            ("FAC-RET-SHA", "Shanghai Retail Fulfilment Hub", "retail_hub", "DOWNSTREAM", "gold", 140, 0.68, "medium", 0.70, "East China", "Shanghai"),
            ("FAC-RET-HGH", "Hangzhou Retail Fulfilment Hub", "retail_hub", "DOWNSTREAM", "gold", 120, 0.64, "medium", 0.68, "East China", "Hangzhou"),
            ("FAC-RET-GUA", "Guangzhou Retail Fulfilment Hub", "retail_hub", "DOWNSTREAM", "gold", 160, 0.69, "medium", 0.69, "South China", "Guangzhou"),
            ("FAC-RET-SZX", "Shenzhen Retail Fulfilment Hub", "retail_hub", "DOWNSTREAM", "gold", 155, 0.71, "medium", 0.69, "South China", "Shenzhen"),
            ("FAC-RET-WUH", "Wuhan Retail Fulfilment Hub", "retail_hub", "DOWNSTREAM", "silver", 125, 0.62, "medium", 0.67, "Central China", "Wuhan"),
            ("FAC-RET-ZZH", "Zhengzhou Retail Fulfilment Hub", "retail_hub", "DOWNSTREAM", "silver", 115, 0.60, "medium", 0.65, "Central China", "Zhengzhou"),
            ("FAC-RET-BEI", "Beijing Retail Fulfilment Hub", "retail_hub", "DOWNSTREAM", "gold", 150, 0.67, "medium", 0.70, "North China", "Beijing"),
            ("FAC-RET-QDA", "Qingdao Retail Fulfilment Hub", "retail_hub", "DOWNSTREAM", "silver", 110, 0.61, "medium", 0.63, "North China", "Qingdao"),
            ("FAC-RET-CDU", "Chengdu Retail Fulfilment Hub", "retail_hub", "DOWNSTREAM", "silver", 115, 0.63, "medium", 0.66, "West China", "Chengdu"),
            ("FAC-RET-HRB", "Harbin Retail Fulfilment Hub", "retail_hub", "DOWNSTREAM", "silver", 95, 0.58, "medium", 0.61, "Northeast China", "Harbin"),
        ]
        city_lookup = {(item.region, item.city): item for item in location_objects}
        for facility_code, name, facility_type, tier_level, cold_level, capacity, util, auto, criticality, region, city in core_facility_specs:
            location = city_lookup[(region, city)]
            facilities.append(
                Facility(
                    facility_code=facility_code,
                    organization_id=focal_org.id,
                    location_id=location.id,
                    name=name,
                    tier_level=tier_level,
                    facility_type=facility_type,
                    cold_chain_level=cold_level,
                    capacity_tonnes_per_week=capacity,
                    utilization_rate=util,
                    automation_level=auto,
                    criticality_index=criticality,
                    active=True,
                )
            )

        carrier_names = [
            "BlueRiver Cold Logistics",
            "NorthGrid Reefer Network",
            "Eastern Silk Road Transport",
            "SouthBay Fresh Lines",
            "Western Resilience Freight",
        ]
        for idx, carrier_name in enumerate(carrier_names, start=1):
            location = rng.choice(location_objects)
            carrier_org = Organization(
                org_code=f"ORG-SVC-{idx:03d}",
                name=carrier_name,
                org_type="carrier",
                business_domain="cold_logistics",
                tier_level="SERVICE",
                primary_material_category="logistics",
                compliance_score=round(rng.uniform(84, 96), 1),
                esg_score=round(rng.uniform(72, 90), 1),
                single_source_dependency=round(rng.uniform(0.12, 0.38), 2),
                geo_risk_index=round(location.climate_risk_index + rng.uniform(0.02, 0.12), 2),
                active=True,
            )
            session.add(carrier_org)
            session.flush()
            organizations.append(carrier_org)
            facilities.append(
                Facility(
                    facility_code=f"FAC-SVC-{idx:03d}",
                    organization_id=carrier_org.id,
                    location_id=location.id,
                    name=f"{carrier_name} Dispatch Hub",
                    tier_level="SERVICE",
                    facility_type="carrier_hub",
                    cold_chain_level="gold",
                    capacity_tonnes_per_week=round(rng.uniform(150, 320), 1),
                    utilization_rate=round(rng.uniform(0.58, 0.79), 2),
                    automation_level="medium",
                    criticality_index=round(rng.uniform(0.45, 0.72), 2),
                    active=True,
                )
            )

        def build_supplier_tier(prefix: str, blueprints: list[tuple[str, str, str, int]], tier_label: str) -> None:
            counter = 1
            for category, org_type, facility_type, count in blueprints:
                for _ in range(count):
                    location = pick_location(rng, locations_by_region, REGIONS)
                    descriptor = category.replace("_", " ").title()
                    org = Organization(
                        org_code=f"ORG-{prefix}-{counter:03d}",
                        name=f"{location.city} {descriptor} {org_type.replace('_', ' ').title()}",
                        org_type=org_type,
                        business_domain="upstream_supply",
                        tier_level=tier_label,
                        primary_material_category=category,
                        compliance_score=round(rng.uniform(76, 97), 1),
                        esg_score=round(rng.uniform(68, 93), 1),
                        single_source_dependency=round(rng.uniform(0.08, 0.68), 2),
                        geo_risk_index=round(min(0.95, location.climate_risk_index + rng.uniform(0.01, 0.22)), 2),
                        active=True,
                    )
                    session.add(org)
                    session.flush()
                    organizations.append(org)
                    facilities.append(
                        Facility(
                            facility_code=f"FAC-{prefix}-{counter:03d}",
                            organization_id=org.id,
                            location_id=location.id,
                            name=f"{location.city} {descriptor} {facility_type.replace('_', ' ').title()}",
                            tier_level=tier_label,
                            facility_type=facility_type,
                            cold_chain_level=rng.choice(["silver", "gold", "platinum"]),
                            capacity_tonnes_per_week=round(rng.uniform(35, 180), 1),
                            utilization_rate=round(rng.uniform(0.49, 0.89), 2),
                            automation_level=rng.choice(["medium", "high"]),
                            criticality_index=round(rng.uniform(0.32, 0.88), 2),
                            active=True,
                        )
                    )
                    counter += 1

        build_supplier_tier("L1", L1_BLUEPRINTS, "L1")
        build_supplier_tier("L2", L2_BLUEPRINTS, "L2")
        build_supplier_tier("L3", L3_BLUEPRINTS, "L3")

        session.add_all(facilities)
        session.flush()

        materials = [
            Material(
                material_code=code,
                name=name,
                category=category,
                unit=unit,
                criticality=criticality,
                cold_chain_required=cold_chain_required,
                base_cost=base_cost,
            )
            for code, name, category, unit, criticality, cold_chain_required, base_cost in MATERIAL_SEEDS
        ]
        products = [
            Product(
                sku_code=sku_code,
                name=name,
                category=category,
                shelf_life_days=shelf_life_days,
                storage_temp_band=temp_band,
                standard_cost=standard_cost,
                unit_price=unit_price,
                target_service_level=0.985 if category in {"protein", "dairy"} else 0.972,
            )
            for sku_code, name, category, shelf_life_days, temp_band, standard_cost, unit_price in PRODUCT_SEEDS
        ]
        session.add_all(materials + products)
        session.flush()

        material_by_code = {item.material_code: item for item in materials}
        product_by_code = {item.sku_code: item for item in products}
        facility_by_code = {item.facility_code: item for item in facilities}
        organization_by_id = {item.id: item for item in organizations}

        bom_rows = []
        for sku_code, materials_spec in BOM_MAP.items():
            for priority_rank, (material_code, qty) in enumerate(materials_spec, start=1):
                bom_rows.append(
                    BillOfMaterial(
                        product_id=product_by_code[sku_code].id,
                        material_id=material_by_code[material_code].id,
                        quantity_per_unit=qty,
                        priority_rank=priority_rank,
                        source_tier_hint="L1",
                    )
                )
        session.add_all(bom_rows)
        session.flush()

        category_to_facilities: dict[str, list[Facility]] = defaultdict(list)
        for facility in facilities:
            org = organization_by_id.get(facility.organization_id)
            if org:
                category_to_facilities[org.primary_material_category].append(facility)

        plant_facilities = [facility_by_code[code] for code in PLANT_PORTFOLIO]
        dc_facilities = [facility for facility in facilities if facility.facility_type == "distribution_center"]
        retail_facilities = [facility for facility in facilities if facility.facility_type == "retail_hub"]

        edges: list[SupplyEdge] = []
        edge_counter = 1
        for plant in plant_facilities:
            sku_codes = PLANT_PORTFOLIO[plant.facility_code]
            needed_material_codes = {code for sku_code in sku_codes for code, _ in BOM_MAP[sku_code]}
            for material_code in needed_material_codes:
                material = material_by_code[material_code]
                candidates = category_to_facilities[material.category]
                for supplier in rng.sample(candidates, k=min(len(candidates), 2 if len(candidates) > 1 else 1)):
                    edges.append(
                        create_supply_edge(
                            f"EDGE-{edge_counter:04d}",
                            supplier,
                            plant,
                            material.id,
                            None,
                            "L1",
                            "material_supply",
                            rng,
                        )
                    )
                    edge_counter += 1

        for category, l2_categories in L2_TO_L1_SUPPORT.items():
            for l1_facility in category_to_facilities[category]:
                for l2_category in l2_categories:
                    candidates = category_to_facilities[l2_category]
                    if not candidates:
                        continue
                    supplier = rng.choice(candidates)
                    edges.append(
                        create_supply_edge(
                            f"EDGE-{edge_counter:04d}",
                            supplier,
                            l1_facility,
                            None,
                            None,
                            "L2",
                            "tier_support",
                            rng,
                        )
                    )
                    edge_counter += 1

        for category, l3_categories in L3_TO_L2_SUPPORT.items():
            for l2_facility in category_to_facilities[category]:
                for l3_category in l3_categories:
                    candidates = category_to_facilities[l3_category]
                    if not candidates:
                        continue
                    supplier = rng.choice(candidates)
                    edges.append(
                        create_supply_edge(
                            f"EDGE-{edge_counter:04d}",
                            supplier,
                            l2_facility,
                            None,
                            None,
                            "L3",
                            "tier_support",
                            rng,
                        )
                    )
                    edge_counter += 1

        for plant in plant_facilities:
            for dc in rng.sample(dc_facilities, k=min(3, len(dc_facilities))):
                for sku_code in PLANT_PORTFOLIO[plant.facility_code]:
                    edges.append(
                        create_supply_edge(
                            f"EDGE-{edge_counter:04d}",
                            plant,
                            dc,
                            None,
                            product_by_code[sku_code].id,
                            "CORE",
                            "distribution",
                            rng,
                        )
                    )
                    edge_counter += 1

        for dc in dc_facilities:
            near_retail = [
                retail
                for retail in retail_facilities
                if origin_location_lookup[retail.location_id].region == origin_location_lookup[dc.location_id].region
            ]
            for retail in near_retail[:2] or retail_facilities[:2]:
                for product in products:
                    if rng.random() < 0.35:
                        edges.append(
                            create_supply_edge(
                                f"EDGE-{edge_counter:04d}",
                                dc,
                                retail,
                                None,
                                product.id,
                                "DOWNSTREAM",
                                "retail_distribution",
                                rng,
                            )
                        )
                        edge_counter += 1

        session.add_all(edges)
        session.flush()

        facility_lookup = {facility.id: facility for facility in facilities}
        inbound_edges_by_material: dict[str, list[SupplyEdge]] = defaultdict(list)
        outbound_edges_by_product: dict[str, list[SupplyEdge]] = defaultdict(list)
        for edge in edges:
            if edge.material_id:
                material_code = next(code for code, material in material_by_code.items() if material.id == edge.material_id)
                inbound_edges_by_material[material_code].append(edge)
            if edge.product_id:
                sku_code = next(code for code, product in product_by_code.items() if product.id == edge.product_id)
                outbound_edges_by_product[sku_code].append(edge)

        direct_material_codes = {material_code for specs in BOM_MAP.values() for material_code, _ in specs}
        supplier_lots: list[SupplierLot] = []
        lot_counter = 1
        for material_code in sorted(direct_material_codes):
            for supplier_facility in category_to_facilities[material_by_code[material_code].category]:
                lot_count = 8 if material_code in {"MAT-BROILER", "MAT-PORK"} else 6
                for _ in range(lot_count):
                    produced_on = today - timedelta(days=rng.randint(2, 80))
                    harvested_on = produced_on - timedelta(days=rng.randint(0, 3))
                    received_on = min(today, produced_on + timedelta(days=rng.randint(1, 5)))
                    inspection_score = round(rng.uniform(83, 99), 2)
                    traceability = round(rng.uniform(0.84, 0.99), 2)
                    supplier_lots.append(
                        SupplierLot(
                            lot_code=f"LOT-{lot_counter:05d}",
                            supplier_facility_id=supplier_facility.id,
                            material_id=material_by_code[material_code].id,
                            produced_on=produced_on,
                            harvested_on=harvested_on,
                            received_on=received_on,
                            quantity_kg=round(rng.uniform(400, 6200), 1),
                            inspection_score=inspection_score,
                            contamination_risk=round(max(0.01, 1 - inspection_score / 100 + rng.uniform(0.0, 0.08)), 3),
                            traceability_completeness=traceability,
                            temperature_excursion_minutes=int(rng.choice([0, 0, 0, 12, 18, 25])),
                        )
                    )
                    lot_counter += 1
        session.add_all(supplier_lots)
        session.flush()

        lots_by_material: dict[str, list[SupplierLot]] = defaultdict(list)
        for lot in supplier_lots:
            material_code = next(code for code, material in material_by_code.items() if material.id == lot.material_id)
            lots_by_material[material_code].append(lot)
        for lot_list in lots_by_material.values():
            lot_list.sort(key=lambda item: item.received_on, reverse=True)

        batches: list[ProductBatch] = []
        batch_usage_rows: list[BatchComponentUsage] = []
        batch_counter = 1
        for days_back in range(60, 0, -1):
            production_day = today - timedelta(days=days_back)
            for plant_code, sku_codes in PLANT_PORTFOLIO.items():
                plant = facility_by_code[plant_code]
                for sku_code in sku_codes:
                    if rng.random() > 0.54:
                        continue
                    product = product_by_code[sku_code]
                    planned_qty = round(rng.uniform(4200, 18000), 1)
                    actual_qty = round(planned_qty * rng.uniform(0.93, 1.02), 1)
                    quality_score = round(rng.uniform(87, 99), 2)
                    batch = ProductBatch(
                        batch_code=f"BAT-{batch_counter:05d}",
                        product_id=product.id,
                        plant_facility_id=plant.id,
                        production_date=production_day,
                        expiry_date=production_day + timedelta(days=product.shelf_life_days),
                        planned_qty=planned_qty,
                        actual_qty=actual_qty,
                        yield_rate=round(actual_qty / planned_qty, 4),
                        status="released",
                        qr_code=f"QR-{product.sku_code}-{batch_counter:05d}",
                        quality_score=quality_score,
                        recall_flag=quality_score < 89 and rng.random() < 0.03,
                    )
                    session.add(batch)
                    session.flush()
                    batches.append(batch)

                    for material_code, qty_per_unit in BOM_MAP[sku_code]:
                        candidate_lots = [
                            lot
                            for lot in lots_by_material[material_code]
                            if lot.received_on <= production_day + timedelta(days=1)
                        ] or lots_by_material[material_code][:3]
                        lot = rng.choice(candidate_lots[: min(6, len(candidate_lots))])
                        batch_usage_rows.append(
                            BatchComponentUsage(
                                product_batch_id=batch.id,
                                supplier_lot_id=lot.id,
                                material_id=material_by_code[material_code].id,
                                quantity_kg=round(actual_qty * qty_per_unit, 2),
                                upstream_depth_label="L1",
                            )
                        )
                    batch_counter += 1
        session.add_all(batch_usage_rows)
        session.flush()

        shipment_rows: list[Shipment] = []
        shipment_counter = 1
        for lot in supplier_lots:
            material_code = next(code for code, material in material_by_code.items() if material.id == lot.material_id)
            candidate_edges = [edge for edge in inbound_edges_by_material[material_code] if edge.from_facility_id == lot.supplier_facility_id]
            if not candidate_edges:
                continue
            edge = rng.choice(candidate_edges)
            dispatched_on = max(lot.produced_on, lot.received_on - timedelta(days=rng.randint(1, 3)))
            planned_hours = max(6.0, edge.transit_distance_km / 55)
            actual_hours = planned_hours * rng.uniform(0.92, 1.28)
            shipment_rows.append(
                Shipment(
                    shipment_code=f"SHP-{shipment_counter:06d}",
                    source_facility_id=edge.from_facility_id,
                    destination_facility_id=edge.to_facility_id,
                    batch_id=None,
                    supplier_lot_id=lot.id,
                    product_id=None,
                    dispatched_at=combine_dt(dispatched_on, rng.randint(1, 9)),
                    arrived_at=combine_dt(lot.received_on, rng.randint(6, 18)),
                    planned_hours=round(planned_hours, 2),
                    actual_hours=round(actual_hours, 2),
                    distance_km=edge.transit_distance_km,
                    temp_min_c=round(rng.uniform(-2, 4), 1),
                    temp_max_c=round(rng.uniform(2, 8), 1),
                    cold_chain_breach_minutes=int(rng.choice([0, 0, 0, 0, 14, 26, 42])),
                    on_time=actual_hours <= planned_hours * 1.05,
                    transport_cost=round(edge.transit_distance_km * rng.uniform(0.8, 1.6), 2),
                    carrier_name=rng.choice(carrier_names),
                    route_risk_score=round(max(5.0, 100 - edge.reliability_score + rng.uniform(3, 15)), 2),
                )
            )
            shipment_counter += 1

        product_distribution_edges = [edge for edge in edges if edge.relation_type in {"distribution", "retail_distribution"}]
        by_source_and_product: dict[tuple[int, int], list[SupplyEdge]] = defaultdict(list)
        for edge in product_distribution_edges:
            if edge.product_id:
                by_source_and_product[(edge.from_facility_id, edge.product_id)].append(edge)

        for batch in batches:
            first_leg_edges = by_source_and_product.get((batch.plant_facility_id, batch.product_id), [])
            if not first_leg_edges:
                continue
            first_leg = rng.choice(first_leg_edges)
            production_day = batch.production_date
            planned_hours = max(4.5, first_leg.transit_distance_km / 58)
            actual_hours = planned_hours * rng.uniform(0.88, 1.23)
            shipment_rows.append(
                Shipment(
                    shipment_code=f"SHP-{shipment_counter:06d}",
                    source_facility_id=first_leg.from_facility_id,
                    destination_facility_id=first_leg.to_facility_id,
                    batch_id=batch.id,
                    supplier_lot_id=None,
                    product_id=batch.product_id,
                    dispatched_at=combine_dt(production_day + timedelta(days=1), rng.randint(5, 11)),
                    arrived_at=combine_dt(production_day + timedelta(days=1), rng.randint(13, 23)),
                    planned_hours=round(planned_hours, 2),
                    actual_hours=round(actual_hours, 2),
                    distance_km=first_leg.transit_distance_km,
                    temp_min_c=round(rng.uniform(-1, 2), 1),
                    temp_max_c=round(rng.uniform(2, 5), 1),
                    cold_chain_breach_minutes=int(rng.choice([0, 0, 0, 8, 16])),
                    on_time=actual_hours <= planned_hours * 1.08,
                    transport_cost=round(first_leg.transit_distance_km * rng.uniform(0.75, 1.45), 2),
                    carrier_name=rng.choice(carrier_names),
                    route_risk_score=round(max(4.0, 100 - first_leg.reliability_score + rng.uniform(2, 12)), 2),
                )
            )
            shipment_counter += 1

            second_leg_edges = by_source_and_product.get((first_leg.to_facility_id, batch.product_id), [])
            if second_leg_edges and rng.random() < 0.84:
                second_leg = rng.choice(second_leg_edges)
                planned_hours_2 = max(2.5, second_leg.transit_distance_km / 45)
                actual_hours_2 = planned_hours_2 * rng.uniform(0.90, 1.30)
                shipment_rows.append(
                    Shipment(
                        shipment_code=f"SHP-{shipment_counter:06d}",
                        source_facility_id=second_leg.from_facility_id,
                        destination_facility_id=second_leg.to_facility_id,
                        batch_id=batch.id,
                        supplier_lot_id=None,
                        product_id=batch.product_id,
                        dispatched_at=combine_dt(production_day + timedelta(days=2), rng.randint(6, 14)),
                        arrived_at=combine_dt(production_day + timedelta(days=2), rng.randint(14, 23)),
                        planned_hours=round(planned_hours_2, 2),
                        actual_hours=round(actual_hours_2, 2),
                        distance_km=second_leg.transit_distance_km,
                        temp_min_c=round(rng.uniform(-1, 3), 1),
                        temp_max_c=round(rng.uniform(2, 6), 1),
                        cold_chain_breach_minutes=int(rng.choice([0, 0, 12, 18, 35])),
                        on_time=actual_hours_2 <= planned_hours_2 * 1.1,
                        transport_cost=round(second_leg.transit_distance_km * rng.uniform(0.7, 1.3), 2),
                        carrier_name=rng.choice(carrier_names),
                        route_risk_score=round(max(5.0, 100 - second_leg.reliability_score + rng.uniform(4, 18)), 2),
                    )
                )
                shipment_counter += 1

        session.add_all(shipment_rows)
        session.flush()

        inspection_rows: list[QualityInspection] = []
        for lot in supplier_lots:
            inspection_rows.append(
                QualityInspection(
                    entity_type="supplier_lot",
                    entity_id=lot.id,
                    facility_id=lot.supplier_facility_id,
                    inspected_at=combine_dt(lot.received_on, rng.randint(5, 18)),
                    inspection_stage="inbound",
                    pathogen_ppm=round(rng.uniform(0.1, 5.2), 3),
                    residue_ppm=round(rng.uniform(0.02, 1.1), 3),
                    package_integrity_score=round(rng.uniform(88, 100), 2),
                    traceability_completeness=lot.traceability_completeness,
                    result="pass" if lot.inspection_score >= 88 else "conditional_pass",
                    notes=f"Tier-tagged upstream lot from {facility_lookup[lot.supplier_facility_id].facility_code}",
                )
            )
        for batch in batches:
            inspection_rows.append(
                QualityInspection(
                    entity_type="product_batch",
                    entity_id=batch.id,
                    facility_id=batch.plant_facility_id,
                    inspected_at=combine_dt(batch.production_date, rng.randint(10, 21)),
                    inspection_stage="finished_goods",
                    pathogen_ppm=round(rng.uniform(0.05, 3.4), 3),
                    residue_ppm=round(rng.uniform(0.01, 0.8), 3),
                    package_integrity_score=round(rng.uniform(90, 100), 2),
                    traceability_completeness=round(rng.uniform(0.90, 0.995), 3),
                    result="pass" if batch.quality_score >= 90 else "hold",
                    notes=f"Batch {batch.batch_code} linked to L1 supplier lots with mesh traceability.",
                )
            )
        session.add_all(inspection_rows)
        session.flush()

        inventory_rows = []
        core_inventory_targets = [facility for facility in facilities if facility.tier_level in {"CORE", "DOWNSTREAM"}]
        for snapshot_day in range(14, 0, -1):
            snapshot_date = today - timedelta(days=snapshot_day)
            for facility in core_inventory_targets:
                freshness_penalty = 0.98 if facility.facility_type == "retail_hub" else 0.995
                for product in products:
                    base = 1800 if facility.facility_type == "retail_hub" else 5600
                    demand_scalar = 1.1 if product.category in {"protein", "dairy"} else 0.88
                    on_hand = round(base * demand_scalar * rng.uniform(0.55, 1.35), 1)
                    safety = round(on_hand * rng.uniform(0.18, 0.34), 1)
                    inventory_rows.append(
                        {
                            "facility_id": facility.id,
                            "item_type": "product",
                            "item_id": product.id,
                            "snapshot_date": snapshot_date,
                            "on_hand_qty": on_hand,
                            "reserved_qty": round(on_hand * rng.uniform(0.1, 0.25), 1),
                            "safety_stock_qty": safety,
                            "days_of_cover": round(on_hand / rng.uniform(180, 520), 2),
                            "freshness_index": round(rng.uniform(0.78, 0.99) * freshness_penalty, 3),
                        }
                    )
        session.execute(InventorySnapshot.__table__.insert(), inventory_rows)
        session.flush()

        demand_rows = []
        demand_start = today - timedelta(days=365)
        region_scalars = {
            "North China": 1.15,
            "East China": 1.28,
            "South China": 1.22,
            "Central China": 1.06,
            "West China": 0.94,
            "Northeast China": 0.83,
        }
        product_base = {
            "SKU-CHB-500": 520,
            "SKU-CHW-1000": 300,
            "SKU-PKL-500": 420,
            "SKU-PKR-800": 260,
            "SKU-TOM-1000": 380,
            "SKU-VEG-600": 340,
            "SKU-DUM-450": 240,
            "SKU-MLK-950": 470,
        }
        for offset in range(365):
            business_date = demand_start + timedelta(days=offset)
            day_of_week = business_date.weekday()
            weekend_boost = 1.16 if day_of_week >= 5 else 1.0
            annual_season = 1 + 0.12 * math.sin((2 * math.pi * offset) / 365)
            festival_index = 1.3 if business_date.month in {1, 9, 10} and business_date.day in range(1, 8) else 1.0
            weather_index = round(float(np.clip(np_rng.normal(1.0, 0.12), 0.72, 1.35)), 3)
            for region in REGIONS:
                for channel in CHANNELS:
                    channel_scalar = 1.12 if channel == "E-Commerce" else 1.0
                    for sku_code, base_units in product_base.items():
                        promo_intensity = round(float(np.clip(np_rng.beta(2.0, 8.0), 0.0, 0.42)), 3)
                        noise = float(np.clip(np_rng.normal(1.0, 0.07), 0.78, 1.28))
                        units = base_units * region_scalars[region] * channel_scalar * annual_season * weather_index * festival_index
                        if sku_code in {"SKU-TOM-1000", "SKU-VEG-600"} and region == "South China":
                            units *= 1.08
                        if sku_code in {"SKU-MLK-950", "SKU-DUM-450"} and channel == "E-Commerce":
                            units *= 1.12
                        units *= (1 + promo_intensity) * weekend_boost * noise
                        price_index = round(float(np.clip(np_rng.normal(1.0, 0.06), 0.85, 1.12)), 3)
                        units_sold = round(units, 1)
                        demand_rows.append(
                            {
                                "business_date": business_date,
                                "region": region,
                                "channel": channel,
                                "product_id": product_by_code[sku_code].id,
                                "units_sold": units_sold,
                                "revenue": round(units_sold * product_by_code[sku_code].unit_price * price_index, 2),
                                "price_index": price_index,
                                "promotion_intensity": promo_intensity,
                                "weather_index": weather_index,
                                "festival_index": festival_index,
                                "waste_units": round(units_sold * rng.uniform(0.006, 0.028), 2),
                            }
                        )
        session.execute(DemandHistory.__table__.insert(), demand_rows)
        session.flush()

        alert_rows = []
        high_risk_edges = sorted(edges, key=lambda edge: edge.reliability_score)[:18]
        for idx, edge in enumerate(high_risk_edges[:12], start=1):
            severity = "critical" if edge.reliability_score < 82 else "high"
            alert_rows.append(
                AlertEvent(
                    event_code=f"ALT-{idx:04d}",
                    organization_id=None,
                    facility_id=edge.to_facility_id,
                    edge_id=edge.id,
                    event_type=rng.choice(["lead_time_volatility", "cold_chain_breach", "supplier_capacity_drop", "port_congestion"]),
                    severity=severity,
                    occurred_at=combine_dt(today - timedelta(days=rng.randint(1, 15)), rng.randint(2, 22)),
                    status=rng.choice(["open", "mitigating", "watching"]),
                    estimated_loss=round(rng.uniform(15000, 240000), 2),
                    description=f"Edge {edge.edge_code} shows abnormal volatility on tier {edge.tier_level} supply line.",
                )
            )
        session.add_all(alert_rows)
        session.flush()
