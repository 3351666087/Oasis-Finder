from __future__ import annotations

import asyncio
from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
import json
import math
import sys
import time
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import get_settings
from .services import (
    get_product_journey,
    get_product_modules,
    load_product_shelf,
    update_product_fields,
)


settings = get_settings()
MEDIA_ROOT = settings.artifact_root / "merchant_media"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
MEDIA_STORE_PATH = settings.runtime_root / "merchant_media_store.json"
DETAIL_STORE_PATH = settings.runtime_root / "merchant_detail_store.json"

app = FastAPI(title="Oasis Finder Web API", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/merchant-media", StaticFiles(directory=str(MEDIA_ROOT)), name="merchant-media")


class ProductUpdate(BaseModel):
    product_name: str | None = None
    category: str | None = None
    unit_price: float | None = None
    shelf_life_days: int | None = None
    storage_temp_band: str | None = None


class MediaUrlUpdate(BaseModel):
    url: str


class DetailUpdate(BaseModel):
    section: str
    item_id: str | None = None
    updates: dict[str, Any]


class DetailCreate(BaseModel):
    section: str
    item: dict[str, Any]


@dataclass
class UpdateBus:
    clients: set[WebSocket]

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.clients.discard(websocket)

    async def broadcast(self, event: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for websocket in list(self.clients):
            try:
                await websocket.send_json(event)
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)


bus = UpdateBus(set())


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list, tuple)):
        return value
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: clean_value(value) for key, value in record.items()}


def records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return [clean_record(row.to_dict()) for _, row in frame.iterrows()]


_DEMO_PAYLOAD_CACHE: dict[str, Any] | None = None
_DATABASE_RETRY_AFTER = 0.0
_DATABASE_RETRY_DELAY_SECONDS = 20.0


def should_try_database() -> bool:
    return time.monotonic() >= _DATABASE_RETRY_AFTER


def mark_database_unavailable() -> None:
    global _DATABASE_RETRY_AFTER
    _DATABASE_RETRY_AFTER = time.monotonic() + _DATABASE_RETRY_DELAY_SECONDS


def demo_payload_path() -> Path:
    candidates = [
        Path(__file__).with_name("demo_payloads.json"),
        Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "mesh_supply_chain" / "demo_payloads.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def read_demo_payloads() -> dict[str, Any]:
    global _DEMO_PAYLOAD_CACHE
    if _DEMO_PAYLOAD_CACHE is None:
        path = demo_payload_path()
        if not path.exists():
            _DEMO_PAYLOAD_CACHE = {"products": [], "details": {}}
        else:
            _DEMO_PAYLOAD_CACHE = json.loads(path.read_text(encoding="utf-8"))
    return _DEMO_PAYLOAD_CACHE


def demo_product_shelf() -> list[dict[str, Any]]:
    payload = deepcopy(read_demo_payloads().get("products", []))
    detail_store = read_detail_store()
    for product in payload:
        overview_overrides = detail_store.get(str(product.get("sku_code", "")), {}).get("overview", {})
        if "product_name" in overview_overrides:
            product["product_name"] = overview_overrides["product_name"]
        if "unit_price" in overview_overrides:
            product["unit_price"] = overview_overrides["unit_price"]
        if "shelf_life_days" in overview_overrides:
            product["shelf_life_days"] = overview_overrides["shelf_life_days"]
        if "storage_temp_band" in overview_overrides:
            product["storage_temp_band"] = overview_overrides["storage_temp_band"]
        if "category" in overview_overrides:
            product["category_label"] = overview_overrides["category"]
        slots = media_slots_for(str(product.get("sku_code", "")))
        primary = next((slot for slot in slots if slot["media_key"] == "product_packshot_url"), None)
        product["primary_media_url"] = primary["url"] if primary else product.get("primary_media_url", "")
    return payload


def demo_product_detail_payload(sku_code: str) -> dict[str, Any]:
    details = read_demo_payloads().get("details", {})
    if sku_code not in details:
        raise ValueError(f"Unknown product SKU: {sku_code}")
    return apply_detail_overrides(sku_code, deepcopy(details[sku_code]))


def safe_product_detail_payload(sku_code: str) -> dict[str, Any]:
    if not should_try_database():
        try:
            return demo_product_detail_payload(sku_code)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        return product_detail_payload(sku_code)
    except ValueError as exc:
        try:
            return demo_product_detail_payload(sku_code)
        except ValueError:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        mark_database_unavailable()
        try:
            return demo_product_detail_payload(sku_code)
        except ValueError:
            raise HTTPException(
                status_code=503,
                detail="Database is unavailable and no packaged demo route exists for this SKU.",
            ) from exc


def read_store() -> dict[str, Any]:
    if not MEDIA_STORE_PATH.exists():
        return {}
    return json.loads(MEDIA_STORE_PATH.read_text(encoding="utf-8"))


def write_store(store: dict[str, Any]) -> None:
    MEDIA_STORE_PATH.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")


def read_detail_store() -> dict[str, Any]:
    if not DETAIL_STORE_PATH.exists():
        return {}
    return json.loads(DETAIL_STORE_PATH.read_text(encoding="utf-8"))


def write_detail_store(store: dict[str, Any]) -> None:
    DETAIL_STORE_PATH.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")


def edge_identity(edge: dict[str, Any]) -> str:
    return "|".join(
        [
            str(edge.get("from_code", "")),
            str(edge.get("to_code", "")),
            str(edge.get("stage", "")),
            str(edge.get("evidence", "")),
        ]
    )


def evidence_identity(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("stage", "")),
            str(row.get("time", "")),
            str(row.get("evidence", "")),
        ]
    )


DETAIL_LIST_SECTIONS = {"modules", "route_nodes", "route_edges", "evidence"}
DETAIL_SECTIONS = {"overview", *DETAIL_LIST_SECTIONS}

STAGE_ORDER = [
    "Raw material origin",
    "Regional aggregation",
    "Ingredient source",
    "Quality / compliance gate",
    "Processing / packing",
    "Distribution center",
    "Logistics node",
    "Retail shelf",
]
FLOW_NODE_WIDTH = 218
FLOW_NODE_HEIGHT = 98
FLOW_PADDING_X = 150
FLOW_PADDING_Y = 92
FLOW_COLUMN_GAP = 330
FLOW_ROW_GAP = 146
FLOW_MIN_WIDTH = 1120
FLOW_MIN_HEIGHT = 620

def generated_code(sku_code: str, suffix: str) -> str:
    return f"{sku_code.lower()}::{suffix}"


def node_title(node: dict[str, Any]) -> str:
    return str(node.get("display_name") or node.get("facility_name") or node.get("facility_code") or "")


def item_identity(section: str, item: dict[str, Any]) -> str:
    if section == "modules":
        return str(item.get("module_id") or f"module-{uuid4().hex[:8]}")
    if section == "route_nodes":
        return str(item.get("facility_code") or f"custom-node-{uuid4().hex[:8]}")
    if section == "route_edges":
        return str(item.get("edge_id") or edge_identity(item))
    if section == "evidence":
        return str(item.get("evidence_id") or evidence_identity(item))
    raise HTTPException(status_code=400, detail=f"Unsupported section: {section}")


def apply_overrides_to_records(
    rows: list[dict[str, Any]],
    id_field: str,
    overrides: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    for row in rows:
        row_id = str(row.get(id_field, ""))
        if row_id in overrides:
            row.update(overrides[row_id])
    return rows


def media_slots_for(sku_code: str, base_slots: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    store = read_store()
    sku_store = store.get(sku_code, {})
    base = records(base_slots) if base_slots is not None and not base_slots.empty else [
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
    for slot in base:
        key = slot["interface_key"].split(".")[-1]
        saved = sku_store.get(key, {})
        slot["media_key"] = key
        slot["url"] = saved.get("url", "")
        slot["source"] = saved.get("source", "placeholder")
    return base


def clamp_percent(value: float) -> float:
    return round(max(4.0, min(96.0, value)), 2)


def number_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def stage_rank(stage: Any) -> int:
    text = str(stage or "")
    try:
        return STAGE_ORDER.index(text)
    except ValueError:
        return len(STAGE_ORDER)


def node_tag_label(node: dict[str, Any]) -> str:
    return str(
        node.get("paint_tag")
        or node.get("tag_label")
        or node.get("material_tag")
        or node.get("facility_type")
        or "Node"
    )


def looks_abstract(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    compact = text.replace("-", "").replace("_", "")
    return compact.isupper() and any(char.isdigit() for char in compact)


def friendly_module_name(product_name: str, module: dict[str, Any], index: int) -> str:
    original = str(module.get("module_name") or "").strip()
    if original and not looks_abstract(original):
        return original
    product_text = product_name.lower()
    cake_names = [
        "Cake sponge base",
        "Fresh cream layer",
        "Fruit topping",
        "Food-contact cake box",
        "Cold-chain gel pack",
        "Decoration and label set",
    ]
    chilled_names = [
        "Main fresh ingredient",
        "Seasoning or dairy input",
        "Packaging material",
        "Cold-chain protection pack",
        "Quality-release certificate",
    ]
    names = cake_names if "cake" in product_text or "蛋糕" in product_text else chilled_names
    return names[index % len(names)]


def add_route_node(nodes_by_code: dict[str, dict[str, Any]], node: dict[str, Any]) -> None:
    code = str(node.get("facility_code") or "")
    if not code:
        return
    cleaned = clean_record(node)
    existing = nodes_by_code.get(code)
    if existing:
        for key, value in cleaned.items():
            if key == "visible_value" and value and value not in str(existing.get(key, "")):
                existing[key] = f"{existing.get(key, '')}; {value}".strip("; ")
            elif value not in (None, "") and key not in {"mesh_x", "mesh_y"}:
                existing.setdefault(key, value)
        return
    cleaned["display_name"] = node_title(cleaned)
    nodes_by_code[code] = cleaned


def add_route_edge(edges_by_id: dict[str, dict[str, Any]], edge: dict[str, Any]) -> None:
    if not edge.get("from_code") or not edge.get("to_code"):
        return
    cleaned = clean_record(edge)
    cleaned["edge_id"] = str(cleaned.get("edge_id") or edge_identity(cleaned))
    edges_by_id.setdefault(cleaned["edge_id"], cleaned)


def strip_tier_fields(payload: dict[str, Any]) -> dict[str, Any]:
    for node in payload.get("route", {}).get("nodes", []):
        node.pop("tier", None)
    for module in payload.get("modules", []):
        module.pop("supplier_tier", None)
        for node in module.get("route_nodes", []):
            node.pop("tier", None)
    return payload


def dedupe_route_edges(edges: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    seen_pairs: set[tuple[str, str]] = set()
    kept: list[dict[str, Any]] = []
    duplicate_ids: list[str] = []
    for edge in edges:
        from_code = str(edge.get("from_code") or "")
        to_code = str(edge.get("to_code") or "")
        if not from_code or not to_code or from_code == to_code:
            duplicate_ids.append(str(edge.get("edge_id") or edge_identity(edge)))
            continue
        pair = tuple(sorted([from_code, to_code]))
        edge_id = str(edge.get("edge_id") or edge_identity(edge))
        if pair in seen_pairs:
            duplicate_ids.append(edge_id)
            continue
        seen_pairs.add(pair)
        kept.append(edge)
    return kept, duplicate_ids


def assign_mesh_layout(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        node["display_name"] = node_title(node)
        stage = str(node.get("stage") or "Ingredient source")
        groups.setdefault(stage, []).append(node)

    ordered_groups = sorted(
        groups.items(),
        key=lambda item: (
            stage_rank(item[0]),
            min(number_or_none(node.get("stage_order")) or 999 for node in item[1]),
            item[0],
        ),
    )
    for _, stage_nodes in ordered_groups:
        stage_nodes.sort(
            key=lambda node: (
                node_tag_label(node),
                number_or_none(node.get("mesh_y")) if number_or_none(node.get("mesh_y")) is not None else 999,
                str(node.get("module_id") or ""),
                node_title(node),
            )
        )

    column_count = max(1, len(ordered_groups))
    max_rows = max([len(stage_nodes) for _, stage_nodes in ordered_groups] or [1])
    width = max(
        FLOW_MIN_WIDTH,
        (FLOW_PADDING_X * 2) + FLOW_NODE_WIDTH + ((column_count - 1) * FLOW_COLUMN_GAP),
    )
    height = max(
        FLOW_MIN_HEIGHT,
        (FLOW_PADDING_Y * 2) + FLOW_NODE_HEIGHT + ((max_rows - 1) * FLOW_ROW_GAP),
    )
    occupied: list[tuple[float, float, float, float]] = []
    bands: list[dict[str, Any]] = []

    def overlaps(x: float, y: float) -> bool:
        left = x - FLOW_NODE_WIDTH / 2
        right = x + FLOW_NODE_WIDTH / 2
        top = y - FLOW_NODE_HEIGHT / 2
        bottom = y + FLOW_NODE_HEIGHT / 2
        for other_left, other_top, other_right, other_bottom in occupied:
            if left < other_right and right > other_left and top < other_bottom and bottom > other_top:
                return True
        return False

    for column_index, (stage, stage_nodes) in enumerate(ordered_groups):
        column_x = FLOW_PADDING_X + (column_index * FLOW_COLUMN_GAP)
        bands.append(
            {
                "stage": stage,
                "x": round(column_x - (FLOW_NODE_WIDTH / 2) - 28, 2),
                "y": 34,
                "width": FLOW_NODE_WIDTH + 56,
                "height": max(160, height - 68),
            }
        )
        for row_index, node in enumerate(stage_nodes):
            saved_x = number_or_none(node.get("mesh_px_x"))
            saved_y = number_or_none(node.get("mesh_px_y"))
            if saved_x is None and number_or_none(node.get("mesh_x")) is not None:
                saved_x = (number_or_none(node.get("mesh_x")) or 0) / 100 * width
            if saved_y is None and number_or_none(node.get("mesh_y")) is not None:
                saved_y = (number_or_none(node.get("mesh_y")) or 0) / 100 * height

            auto_x = column_x
            auto_y = FLOW_PADDING_Y + (row_index * FLOW_ROW_GAP) + ((column_index % 2) * 12)
            use_saved_layout = bool(node.get("layout_locked") or node.get("_custom"))
            x = saved_x if saved_x is not None and use_saved_layout else auto_x
            y = saved_y if saved_y is not None and use_saved_layout else auto_y
            x = max(FLOW_PADDING_X / 2, min(width - FLOW_PADDING_X / 2, x))
            y = max(FLOW_PADDING_Y / 2, min(height - FLOW_PADDING_Y / 2, y))

            while overlaps(x, y):
                y += FLOW_ROW_GAP
                if y + (FLOW_NODE_HEIGHT / 2) + FLOW_PADDING_Y > height:
                    height += FLOW_ROW_GAP
                    for band in bands:
                        band["height"] = max(160, height - 68)

            node["mesh_px_x"] = round(x, 2)
            node["mesh_px_y"] = round(y, 2)
            node["mesh_x"] = clamp_percent((x / width) * 100)
            node["mesh_y"] = clamp_percent((y / height) * 100)
            occupied.append(
                (
                    x - FLOW_NODE_WIDTH / 2,
                    y - FLOW_NODE_HEIGHT / 2,
                    x + FLOW_NODE_WIDTH / 2,
                    y + FLOW_NODE_HEIGHT / 2,
                )
            )

    return {
        "width": round(width, 2),
        "height": round(height, 2),
        "node_width": FLOW_NODE_WIDTH,
        "node_height": FLOW_NODE_HEIGHT,
        "padding_x": FLOW_PADDING_X,
        "padding_y": FLOW_PADDING_Y,
        "column_gap": FLOW_COLUMN_GAP,
        "row_gap": FLOW_ROW_GAP,
        "bands": bands,
    }


def enrich_payload_mesh(sku_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    overview = payload.get("overview", {})
    product_name = str(overview.get("product_name") or "product")
    plant_code = str(overview.get("plant_code") or "")
    plant_city = str(overview.get("plant_city") or "")

    nodes_by_code: dict[str, dict[str, Any]] = {}
    edges_by_id: dict[str, dict[str, Any]] = {}
    for node in payload["route"]["nodes"]:
        add_route_node(nodes_by_code, node)
    for edge in payload["route"]["edges"]:
        add_route_edge(edges_by_id, edge)

    for index, module in enumerate(payload.get("modules", [])):
        module_name = friendly_module_name(product_name, module, index)
        module["display_module_name"] = module_name
        module_id = str(module.get("module_id") or f"module-{index + 1}")
        supplier_code = str(module.get("supplier_code") or "")
        supplier_city = str(module.get("supplier_city") or plant_city or "Supplier city")
        y_anchor = 14 + (index % 5) * 15

        origin_code = generated_code(sku_code, f"{module_id}-origin")
        collector_code = generated_code(sku_code, f"{module_id}-collection")
        lab_code = generated_code(sku_code, f"{module_id}-lab")

        add_route_node(
            nodes_by_code,
            {
                "facility_code": origin_code,
                "display_name": f"{module_name} origin producer",
                "facility_name": f"{module_name} origin producer",
                "stage": "Raw material origin",
                "stage_order": 0,
                "paint_tag": "Raw material",
                "paint_color": "#67e8f9",
                "facility_type": "farm_or_primary_source",
                "city": supplier_city,
                "role": "Origin producer",
                "visible_value": f"{module_name}: origin date, producer identity, and raw-material lot proof.",
                "mesh_x": 8,
                "mesh_y": clamp_percent(y_anchor),
                "module_id": module_id,
                "generated_demo": True,
            },
        )
        add_route_node(
            nodes_by_code,
            {
                "facility_code": collector_code,
                "display_name": f"{module_name} collection and pre-cooling hub",
                "facility_name": f"{module_name} collection and pre-cooling hub",
                "stage": "Regional aggregation",
                "stage_order": 1,
                "paint_tag": "Collection",
                "paint_color": "#a78bfa",
                "facility_type": "collection_hub",
                "city": supplier_city,
                "role": "Lot consolidation",
                "visible_value": f"{module_name}: receiving time, lot merge rule, pre-cooling result, and handover proof.",
                "mesh_x": 22,
                "mesh_y": clamp_percent(y_anchor + 6),
                "module_id": module_id,
                "generated_demo": True,
            },
        )
        add_route_node(
            nodes_by_code,
            {
                "facility_code": lab_code,
                "display_name": f"{module_name} quality-release lab",
                "facility_name": f"{module_name} quality-release lab",
                "stage": "Quality / compliance gate",
                "stage_order": 1,
                "paint_tag": "Quality gate",
                "paint_color": "#86efac",
                "facility_type": "quality_lab",
                "city": supplier_city,
                "role": "Inspection and release",
                "visible_value": f"{module_name}: inspection score, residue/pathogen check, certificate ID, and release result.",
                "mesh_x": 43,
                "mesh_y": clamp_percent(y_anchor + 2),
                "module_id": module_id,
                "generated_demo": True,
            },
        )
        if supplier_code and supplier_code in nodes_by_code:
            nodes_by_code[supplier_code]["display_name"] = (
                nodes_by_code[supplier_code].get("facility_name") or f"{module_name} primary supplier"
            )
            nodes_by_code[supplier_code].setdefault("module_id", module_id)
            nodes_by_code[supplier_code]["mesh_x"] = nodes_by_code[supplier_code].get("mesh_x") or 34
            nodes_by_code[supplier_code]["mesh_y"] = nodes_by_code[supplier_code].get("mesh_y") or clamp_percent(y_anchor + 11)
            add_route_edge(
                edges_by_id,
                {
                    "from_code": origin_code,
                    "to_code": collector_code,
                    "flow": f"{module_name} raw lot",
                    "stage": "origin_to_collection",
                    "evidence": f"{module_name} origin record",
                    "metric": "producer ID | harvest / production date | lot size",
                    "quality_risk": "origin risk, certificate status, and basic freshness check",
                    "temperature": "pre-cooling requirement recorded",
                    "traceability": "origin -> collection",
                    "module_id": module_id,
                },
            )
            add_route_edge(
                edges_by_id,
                {
                    "from_code": collector_code,
                    "to_code": supplier_code,
                    "flow": f"{module_name} consolidated lot",
                    "stage": "collection_to_supplier",
                    "evidence": str(module.get("lot_code") or f"{module_name} lot"),
                    "metric": f"received {module.get('received_on') or 'editable time'} | supplier handoff",
                    "quality_risk": "lot merge rule and storage condition",
                    "temperature": f"{module.get('temperature_excursion_minutes') or 0} min excursion",
                    "traceability": "collection -> supplier",
                    "module_id": module_id,
                },
            )
            add_route_edge(
                edges_by_id,
                {
                    "from_code": supplier_code,
                    "to_code": lab_code,
                    "flow": f"{module_name} sample",
                    "stage": "supplier_to_lab",
                    "evidence": f"{module_name} test sample",
                    "metric": f"inspection {module.get('inspection_score') or 'editable'}",
                    "quality_risk": f"contamination risk {module.get('contamination_risk') or 'editable'}",
                    "temperature": "sample condition recorded",
                    "traceability": "supplier -> QC",
                    "module_id": module_id,
                },
            )
        if plant_code:
            add_route_edge(
                edges_by_id,
                {
                    "from_code": lab_code,
                    "to_code": plant_code,
                    "flow": f"{module_name} release signal",
                    "stage": "lab_to_plant_release",
                    "evidence": f"{module_name} release certificate",
                    "metric": "release result | certificate ID | accepted quantity",
                    "quality_risk": "only released lots enter production",
                    "temperature": str(overview.get("storage_temp_band") or "controlled"),
                    "traceability": "QC -> CORE",
                    "module_id": module_id,
                },
            )

    downstream = [
        node for node in nodes_by_code.values()
        if node.get("stage") in {"Distribution center", "Retail shelf", "Logistics node"}
    ]
    if plant_code:
        packaging_code = generated_code(sku_code, "packaging-compliance")
        sensor_code = generated_code(sku_code, "cold-chain-sensor")
        add_route_node(
            nodes_by_code,
            {
                "facility_code": packaging_code,
                "display_name": f"{product_name} packaging compliance file",
                "facility_name": f"{product_name} packaging compliance file",
                "stage": "Quality / compliance gate",
                "stage_order": 1,
                "paint_tag": "Quality gate",
                "paint_color": "#86efac",
                "facility_type": "packaging_compliance",
                "city": plant_city,
                "role": "Food-contact material and label check",
                "visible_value": "Material safety statement, label version, allergen claim, and seal integrity.",
                "mesh_x": 45,
                "mesh_y": 82,
                "generated_demo": True,
            },
        )
        add_route_edge(
            edges_by_id,
            {
                "from_code": packaging_code,
                "to_code": plant_code,
                "flow": "packaging release",
                "stage": "packaging_to_plant",
                "evidence": "packaging compliance record",
                "metric": "label version | food-contact material | seal score",
                "quality_risk": "allergen and label mismatch risk",
                "temperature": "",
                "traceability": "Packaging -> CORE",
            },
        )
        add_route_node(
            nodes_by_code,
            {
                "facility_code": sensor_code,
                "display_name": f"{product_name} cold-chain sensor gateway",
                "facility_name": f"{product_name} cold-chain sensor gateway",
                "stage": "Logistics node",
                "stage_order": 3,
                "paint_tag": "Logistics",
                "paint_color": "#f472b6",
                "facility_type": "sensor_gateway",
                "city": plant_city,
                "role": "Temperature and carrier telemetry",
                "visible_value": "Temperature range, breach minutes, carrier, dispatch time, and arrival time.",
                "mesh_x": 69,
                "mesh_y": 74,
                "generated_demo": True,
            },
        )
        target_code = str(downstream[0].get("facility_code")) if downstream else plant_code
        add_route_edge(
            edges_by_id,
            {
                "from_code": plant_code,
                "to_code": sensor_code,
                "flow": "finished product telemetry",
                "stage": "plant_to_sensor",
                "evidence": "temperature logger activation",
                "metric": "dispatch time | logger ID | target temp band",
                "quality_risk": "cold-chain breach visibility",
                "temperature": str(overview.get("storage_temp_band") or "controlled"),
                "traceability": "CORE -> sensor",
            },
        )
        if target_code != plant_code:
            add_route_edge(
                edges_by_id,
                {
                    "from_code": sensor_code,
                    "to_code": target_code,
                    "flow": "validated cold-chain handoff",
                    "stage": "sensor_to_distribution",
                    "evidence": "arrival temperature log",
                    "metric": "arrival time | min/max temp | breach minutes",
                    "quality_risk": "carrier and route risk",
                    "temperature": str(overview.get("storage_temp_band") or "controlled"),
                    "traceability": "sensor -> downstream",
                },
            )

    nodes = list(nodes_by_code.values())
    edges = list(edges_by_id.values())
    payload["route"]["layout"] = assign_mesh_layout(nodes)
    valid_codes = {str(node.get("facility_code")) for node in nodes}
    edges = [edge for edge in edges if str(edge.get("from_code")) in valid_codes and str(edge.get("to_code")) in valid_codes]
    edges, _ = dedupe_route_edges(edges)
    payload["route"]["nodes"] = nodes
    payload["route"]["edges"] = edges

    plant_and_downstream = {
        str(node.get("facility_code"))
        for node in nodes
        if node.get("stage") in {"Processing / packing", "Distribution center", "Retail shelf", "Logistics node"}
    }
    for module in payload.get("modules", []):
        module_id = str(module.get("module_id") or "")
        supplier_code = str(module.get("supplier_code") or "")
        module_codes = {
            str(node.get("facility_code"))
            for node in nodes
            if str(node.get("module_id") or "") == module_id
        }
        if supplier_code:
            module_codes.add(supplier_code)
        module_codes.update(plant_and_downstream)
        module["route_nodes"] = [dict(node) for node in nodes if str(node.get("facility_code")) in module_codes]
        module["route_edges"] = [
            dict(edge) for edge in edges
            if str(edge.get("module_id") or "") == module_id
            or (str(edge.get("from_code")) in module_codes and str(edge.get("to_code")) in module_codes)
        ]
        module["route_layout"] = assign_mesh_layout(module["route_nodes"])

    overview["route_node_count"] = len(nodes)
    overview["route_edge_count"] = len(edges)
    return strip_tier_fields(payload)


def module_routes(sku_code: str, modules: pd.DataFrame, journey: dict[str, Any]) -> list[dict[str, Any]]:
    route_nodes = journey["route_nodes"]
    route_edges = journey["route_edges"]
    module_payload: list[dict[str, Any]] = []
    for _, row in modules.iterrows():
        supplier_code = row.get("supplier_code")
        if pd.isna(supplier_code):
            supplier_code = None
        plant_code = journey["overview"].get("plant_code")
        module_id = str(row.get("module_id"))
        supplier_nodes = route_nodes[route_nodes["facility_code"].isin([supplier_code, plant_code])] if not route_nodes.empty else pd.DataFrame()
        supplier_edges = route_edges[
            (route_edges["from_code"] == supplier_code) & (route_edges["to_code"] == plant_code)
        ] if not route_edges.empty and supplier_code and plant_code else pd.DataFrame()
        module_payload.append(
            {
                **clean_record(row.to_dict()),
                "module_id": module_id,
                "route_nodes": records(supplier_nodes),
                "route_edges": records(supplier_edges),
            }
        )
    return module_payload


def product_detail_payload(sku_code: str) -> dict[str, Any]:
    journey = get_product_journey(sku_code)
    modules = get_product_modules(sku_code)
    media_slots = media_slots_for(sku_code, journey.get("media_slots", pd.DataFrame()))
    route_nodes = records(journey["route_nodes"])
    route_edges = records(journey["route_edges"])
    for edge in route_edges:
        edge["edge_id"] = edge_identity(edge)
    module_payload = module_routes(sku_code, modules, journey)
    for module in module_payload:
        for edge in module.get("route_edges", []):
            edge["edge_id"] = edge_identity(edge)
    evidence = records(journey["evidence"])
    for row in evidence:
        row["evidence_id"] = evidence_identity(row)

    payload = {
        "overview": clean_record(journey["overview"]),
        "route": {
            "nodes": route_nodes,
            "edges": route_edges,
        },
        "modules": module_payload,
        "media_slots": media_slots,
        "evidence": evidence,
    }
    payload = enrich_payload_mesh(sku_code, payload)
    return apply_detail_overrides(sku_code, payload)


def apply_detail_overrides(sku_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    sku_store = read_detail_store().get(sku_code, {})
    payload["overview"].update(sku_store.get("overview", {}))

    deleted = {
        section: set(map(str, sku_store.get("_deleted", {}).get(section, [])))
        for section in DETAIL_LIST_SECTIONS
    }

    def merge_section(section: str, rows: list[dict[str, Any]], id_field: str) -> list[dict[str, Any]]:
        overrides = sku_store.get(section, {})
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            row_id = str(row.get(id_field, ""))
            if row_id in deleted[section]:
                continue
            next_row = {**row, **overrides.get(row_id, {})}
            if section == "route_edges":
                next_row["edge_id"] = str(next_row.get("edge_id") or edge_identity(next_row))
                row_id = next_row["edge_id"]
            merged.append(next_row)
            seen.add(row_id)
        for row_id, override in overrides.items():
            if str(row_id) in deleted[section] or str(row_id) in seen:
                continue
            next_row = {"_custom": True, **override}
            next_row[id_field] = next_row.get(id_field) or str(row_id)
            if section == "route_edges":
                next_row["edge_id"] = str(next_row.get("edge_id") or edge_identity(next_row))
            merged.append(next_row)
        return merged

    payload["modules"] = merge_section("modules", payload["modules"], "module_id")
    payload["route"]["nodes"] = merge_section("route_nodes", payload["route"]["nodes"], "facility_code")
    payload["route"]["edges"] = merge_section("route_edges", payload["route"]["edges"], "edge_id")
    payload["route"]["edges"], duplicate_edge_ids = dedupe_route_edges(payload["route"]["edges"])
    if duplicate_edge_ids:
        deleted_edges = sku_store.setdefault("_deleted", {}).setdefault("route_edges", [])
        for edge_id in duplicate_edge_ids:
            sku_store.setdefault("route_edges", {}).pop(edge_id, None)
            if edge_id not in deleted_edges:
                deleted_edges.append(edge_id)
        store = read_detail_store()
        store.setdefault(sku_code, {}).update(sku_store)
        write_detail_store(store)
    payload["evidence"] = merge_section("evidence", payload["evidence"], "evidence_id")

    valid_node_codes = {str(node.get("facility_code")) for node in payload["route"]["nodes"]}
    payload["route"]["edges"] = [
        edge for edge in payload["route"]["edges"]
        if str(edge.get("from_code")) in valid_node_codes and str(edge.get("to_code")) in valid_node_codes
    ]

    for module in payload["modules"]:
        module["route_nodes"] = merge_section("route_nodes", module.get("route_nodes", []), "facility_code")
        module_codes = {str(node.get("facility_code")) for node in module.get("route_nodes", [])}
        module["route_edges"] = [
            edge for edge in merge_section("route_edges", module.get("route_edges", []), "edge_id")
            if str(edge.get("from_code")) in module_codes and str(edge.get("to_code")) in module_codes
        ]
        module["route_edges"], _ = dedupe_route_edges(module["route_edges"])
        module["route_layout"] = assign_mesh_layout(module["route_nodes"])

    payload["route"]["layout"] = assign_mesh_layout(payload["route"]["nodes"])
    payload["overview"]["route_node_count"] = len(payload["route"]["nodes"])
    payload["overview"]["route_edge_count"] = len(payload["route"]["edges"])

    return strip_tier_fields(payload)


@app.get("/api/health")
def api_health() -> dict[str, str]:
    return {"status": "ok", "service": "oasis-finder-web-api"}


@app.get("/api/products")
def api_products() -> list[dict[str, Any]]:
    if should_try_database():
        try:
            shelf = load_product_shelf()
            payload = records(shelf)
        except Exception as exc:
            mark_database_unavailable()
            payload = demo_product_shelf()
            if not payload:
                raise HTTPException(
                    status_code=503,
                    detail="Database is unavailable and no packaged demo products are available.",
                ) from exc
    else:
        payload = demo_product_shelf()
        if not payload:
            raise HTTPException(
                status_code=503,
                detail="Database is unavailable and no packaged demo products are available.",
            )
    for product in payload:
        slots = media_slots_for(str(product["sku_code"]))
        primary = next((slot for slot in slots if slot["media_key"] == "product_packshot_url"), None)
        product["primary_media_url"] = primary["url"] if primary else ""
    return payload


@app.get("/api/products/{sku_code}")
def api_product_detail(sku_code: str) -> dict[str, Any]:
    return safe_product_detail_payload(sku_code)


@app.patch("/api/admin/products/{sku_code}")
async def api_update_product(sku_code: str, payload: ProductUpdate) -> dict[str, Any]:
    updates = (
        payload.model_dump(exclude_unset=True)
        if hasattr(payload, "model_dump")
        else payload.dict(exclude_unset=True)
    )
    try:
        if not should_try_database():
            raise RuntimeError("Database retry delay is active; saving product fields to packaged demo store.")
        result = update_product_fields(sku_code, updates)
    except Exception:
        mark_database_unavailable()
        store = read_detail_store()
        store.setdefault(sku_code, {}).setdefault("overview", {}).update(clean_record(updates))
        write_detail_store(store)
        result = {
            "updated": bool(updates),
            "sku_code": sku_code,
            "fields": list(updates.keys()),
            "storage": "packaged_demo_override",
        }
    await bus.broadcast({"type": "product.updated", "sku_code": sku_code, "result": result})
    return {"ok": True, **result}


@app.put("/api/admin/products/{sku_code}/media/{media_key}")
async def api_update_media_url(sku_code: str, media_key: str, payload: MediaUrlUpdate) -> dict[str, Any]:
    store = read_store()
    store.setdefault(sku_code, {})[media_key] = {"url": payload.url, "source": "url"}
    write_store(store)
    await bus.broadcast({"type": "media.updated", "sku_code": sku_code, "media_key": media_key})
    return {"ok": True, "sku_code": sku_code, "media_key": media_key, "url": payload.url}


@app.post("/api/admin/products/{sku_code}/media/{media_key}/upload")
async def api_upload_media(sku_code: str, media_key: str, file: UploadFile = File(...)) -> dict[str, Any]:
    suffix = Path(file.filename or "").suffix.lower() or ".png"
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=400, detail="Only png, jpg, jpeg, or webp images are supported.")
    target_dir = MEDIA_ROOT / sku_code
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{media_key}{suffix}"
    content = await file.read()
    target.write_bytes(content)
    url = f"/merchant-media/{sku_code}/{target.name}"
    store = read_store()
    store.setdefault(sku_code, {})[media_key] = {"url": url, "source": "upload"}
    write_store(store)
    await bus.broadcast({"type": "media.updated", "sku_code": sku_code, "media_key": media_key})
    return {"ok": True, "sku_code": sku_code, "media_key": media_key, "url": url}


@app.patch("/api/admin/products/{sku_code}/detail")
async def api_update_detail(sku_code: str, payload: DetailUpdate) -> dict[str, Any]:
    if payload.section not in DETAIL_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported section: {payload.section}")
    if payload.section != "overview" and not payload.item_id:
        raise HTTPException(status_code=400, detail="item_id is required for this section.")

    store = read_detail_store()
    sku_store = store.setdefault(sku_code, {})
    cleaned_updates = clean_record(payload.updates)

    if payload.section == "overview":
        sku_store.setdefault("overview", {}).update(cleaned_updates)
        item_id = "overview"
    else:
        item_id = str(payload.item_id)
        if payload.section == "route_edges" and {"from_code", "to_code"} & set(cleaned_updates):
            detail = safe_product_detail_payload(sku_code)
            current_edge = next(
                (
                    edge for edge in detail.get("route", {}).get("edges", [])
                    if str(edge.get("edge_id") or edge_identity(edge)) == item_id
                ),
                {},
            )
            next_from = str(cleaned_updates.get("from_code") or current_edge.get("from_code") or "")
            next_to = str(cleaned_updates.get("to_code") or current_edge.get("to_code") or "")
            if not next_from or not next_to or next_from == next_to:
                raise HTTPException(status_code=400, detail="Route edge requires two different nodes.")
            existing_edge = next(
                (
                    edge for edge in detail.get("route", {}).get("edges", [])
                    if str(edge.get("edge_id") or edge_identity(edge)) != item_id
                    and {str(edge.get("from_code")), str(edge.get("to_code"))} == {next_from, next_to}
                ),
                None,
            )
            if existing_edge:
                raise HTTPException(status_code=409, detail="These two nodes are already connected.")
        sku_store.setdefault(payload.section, {}).setdefault(item_id, {}).update(cleaned_updates)

    write_detail_store(store)
    await bus.broadcast(
        {
            "type": "detail.updated",
            "sku_code": sku_code,
            "section": payload.section,
            "item_id": item_id,
        }
    )
    return {"ok": True, "sku_code": sku_code, "section": payload.section, "item_id": item_id}


@app.post("/api/admin/products/{sku_code}/detail")
async def api_create_detail(sku_code: str, payload: DetailCreate) -> dict[str, Any]:
    if payload.section not in DETAIL_LIST_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported create section: {payload.section}")

    store = read_detail_store()
    sku_store = store.setdefault(sku_code, {})
    cleaned_item = clean_record(payload.item)
    item_id = item_identity(payload.section, cleaned_item)
    if payload.section == "route_edges":
        from_code = str(cleaned_item.get("from_code") or "")
        to_code = str(cleaned_item.get("to_code") or "")
        if not from_code or not to_code or from_code == to_code:
            raise HTTPException(status_code=400, detail="Route edge requires two different nodes.")
        detail = safe_product_detail_payload(sku_code)
        existing_edge = next(
            (
                edge for edge in detail.get("route", {}).get("edges", [])
                if {str(edge.get("from_code")), str(edge.get("to_code"))} == {from_code, to_code}
            ),
            None,
        )
        if existing_edge:
            raise HTTPException(status_code=409, detail="These two nodes are already connected.")

    if payload.section == "modules":
        cleaned_item["module_id"] = item_id
    elif payload.section == "route_nodes":
        cleaned_item["facility_code"] = item_id
        cleaned_item.setdefault("display_name", cleaned_item.get("facility_name") or "New supply-chain node")
    elif payload.section == "route_edges":
        cleaned_item["edge_id"] = item_id
    elif payload.section == "evidence":
        cleaned_item["evidence_id"] = item_id

    sku_store.setdefault(payload.section, {})[item_id] = cleaned_item
    deleted = sku_store.setdefault("_deleted", {}).setdefault(payload.section, [])
    sku_store["_deleted"][payload.section] = [row_id for row_id in deleted if str(row_id) != item_id]
    write_detail_store(store)
    await bus.broadcast(
        {
            "type": "detail.created",
            "sku_code": sku_code,
            "section": payload.section,
            "item_id": item_id,
        }
    )
    return {"ok": True, "sku_code": sku_code, "section": payload.section, "item_id": item_id, "item": cleaned_item}


@app.delete("/api/admin/products/{sku_code}/detail/{section}/{item_id}")
async def api_delete_detail(sku_code: str, section: str, item_id: str) -> dict[str, Any]:
    if section not in DETAIL_LIST_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported delete section: {section}")

    store = read_detail_store()
    sku_store = store.setdefault(sku_code, {})
    item_ids = {str(item_id)}
    if section == "route_edges":
        detail = safe_product_detail_payload(sku_code)
        for edge in detail.get("route", {}).get("edges", []):
            edge_ids = {str(edge.get("edge_id") or ""), edge_identity(edge)}
            if str(item_id) in edge_ids:
                item_ids.update(edge_id for edge_id in edge_ids if edge_id)

    deleted = sku_store.setdefault("_deleted", {}).setdefault(section, [])
    for row_id in item_ids:
        sku_store.setdefault(section, {}).pop(row_id, None)
        if row_id not in deleted:
            deleted.append(row_id)

    if section == "route_nodes":
        detail = safe_product_detail_payload(sku_code)
        connected_edges = [
            str(edge.get("edge_id") or edge_identity(edge))
            for edge in detail.get("route", {}).get("edges", [])
            if str(edge.get("from_code")) == item_id or str(edge.get("to_code")) == item_id
        ]
        edge_deleted = sku_store.setdefault("_deleted", {}).setdefault("route_edges", [])
        for edge_id in connected_edges:
            sku_store.setdefault("route_edges", {}).pop(edge_id, None)
            if edge_id not in edge_deleted:
                edge_deleted.append(edge_id)

    write_detail_store(store)
    await bus.broadcast(
        {
            "type": "detail.deleted",
            "sku_code": sku_code,
            "section": section,
            "item_id": item_id,
        }
    )
    return {"ok": True, "sku_code": sku_code, "section": section, "item_id": item_id}


@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket) -> None:
    await bus.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        bus.disconnect(websocket)
    except RuntimeError:
        bus.disconnect(websocket)


def packaged_web_dist() -> Path | None:
    candidates = [
        Path(getattr(sys, "_MEIPASS", settings.project_root)) / "web" / "dist",
        settings.project_root / "web" / "dist",
    ]
    for candidate in candidates:
        if (candidate / "index.html").exists():
            return candidate
    return None


WEB_DIST = packaged_web_dist()
if WEB_DIST and (WEB_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIST / "assets")), name="web-assets")


@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    if not WEB_DIST:
        raise HTTPException(status_code=404, detail="Frontend build not found. Run npm run build in web/.")
    return FileResponse(WEB_DIST / "index.html")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str) -> FileResponse:
    if not WEB_DIST:
        raise HTTPException(status_code=404, detail="Frontend build not found. Run npm run build in web/.")
    candidate = WEB_DIST / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(WEB_DIST / "index.html")


def main() -> None:
    import uvicorn

    uvicorn.run("mesh_supply_chain.web_api:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
