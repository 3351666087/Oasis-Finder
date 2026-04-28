from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
import json
import math
import sys
from typing import Any

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
    return apply_detail_overrides(sku_code, payload)


def apply_detail_overrides(sku_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    sku_store = read_detail_store().get(sku_code, {})
    payload["overview"].update(sku_store.get("overview", {}))

    module_overrides = sku_store.get("modules", {})
    node_overrides = sku_store.get("route_nodes", {})
    edge_overrides = sku_store.get("route_edges", {})
    evidence_overrides = sku_store.get("evidence", {})

    apply_overrides_to_records(payload["modules"], "module_id", module_overrides)
    apply_overrides_to_records(payload["route"]["nodes"], "facility_code", node_overrides)
    apply_overrides_to_records(payload["route"]["edges"], "edge_id", edge_overrides)
    apply_overrides_to_records(payload["evidence"], "evidence_id", evidence_overrides)

    for module in payload["modules"]:
        apply_overrides_to_records(module.get("route_nodes", []), "facility_code", node_overrides)
        apply_overrides_to_records(module.get("route_edges", []), "edge_id", edge_overrides)

    return payload


@app.get("/api/health")
def api_health() -> dict[str, str]:
    return {"status": "ok", "service": "oasis-finder-web-api"}


@app.get("/api/products")
def api_products() -> list[dict[str, Any]]:
    shelf = load_product_shelf()
    payload = records(shelf)
    for product in payload:
        slots = media_slots_for(str(product["sku_code"]))
        primary = next((slot for slot in slots if slot["media_key"] == "product_packshot_url"), None)
        product["primary_media_url"] = primary["url"] if primary else ""
    return payload


@app.get("/api/products/{sku_code}")
def api_product_detail(sku_code: str) -> dict[str, Any]:
    try:
        return product_detail_payload(sku_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/admin/products/{sku_code}")
async def api_update_product(sku_code: str, payload: ProductUpdate) -> dict[str, Any]:
    updates = (
        payload.model_dump(exclude_unset=True)
        if hasattr(payload, "model_dump")
        else payload.dict(exclude_unset=True)
    )
    result = update_product_fields(sku_code, updates)
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
    valid_sections = {"overview", "modules", "route_nodes", "route_edges", "evidence"}
    if payload.section not in valid_sections:
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
