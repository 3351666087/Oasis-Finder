from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy import text
from xgboost import XGBRegressor

from .config import get_settings
from .db import create_app_engine, session_scope
from .models import ForecastResult, RiskAssessment


def _engine():
    return create_app_engine()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _risk_feature_frame() -> pd.DataFrame:
    query = text(
        """
        SELECT
            f.id AS facility_id,
            f.facility_code,
            f.name AS facility_name,
            f.tier_level,
            f.facility_type,
            o.org_code,
            o.name AS organization_name,
            o.compliance_score,
            o.esg_score,
            o.single_source_dependency,
            o.geo_risk_index,
            f.capacity_tonnes_per_week,
            f.utilization_rate,
            f.criticality_index,
            COALESCE(e.inbound_edge_count, 0) AS inbound_edge_count,
            COALESCE(e.avg_reliability, 95) AS avg_reliability,
            COALESCE(e.avg_lead_time, 2) AS avg_lead_time,
            COALESCE(s.avg_breach, 0) AS avg_cold_breach,
            COALESCE(s.on_time_rate, 0.96) AS on_time_rate,
            COALESCE(s.shipment_count, 0) AS shipment_count,
            COALESCE(q.traceability_score, 0.95) AS traceability_score,
            COALESCE(q.pass_rate, 0.97) AS inspection_pass_rate,
            COALESCE(a.critical_alerts, 0) AS critical_alerts,
            COALESCE(a.alert_count, 0) AS alert_count
        FROM facilities f
        JOIN organizations o ON o.id = f.organization_id
        LEFT JOIN (
            SELECT
                to_facility_id AS facility_id,
                COUNT(*) AS inbound_edge_count,
                AVG(reliability_score) AS avg_reliability,
                AVG(lead_time_days) AS avg_lead_time
            FROM supply_edges
            WHERE active = 1
            GROUP BY to_facility_id
        ) e ON e.facility_id = f.id
        LEFT JOIN (
            SELECT
                destination_facility_id AS facility_id,
                AVG(cold_chain_breach_minutes) AS avg_breach,
                AVG(CASE WHEN on_time THEN 1 ELSE 0 END) AS on_time_rate,
                COUNT(*) AS shipment_count
            FROM shipments
            GROUP BY destination_facility_id
        ) s ON s.facility_id = f.id
        LEFT JOIN (
            SELECT
                facility_id,
                AVG(traceability_completeness) AS traceability_score,
                AVG(CASE WHEN result = 'pass' THEN 1 ELSE 0 END) AS pass_rate
            FROM quality_inspections
            GROUP BY facility_id
        ) q ON q.facility_id = f.id
        LEFT JOIN (
            SELECT
                facility_id,
                SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) AS critical_alerts,
                COUNT(*) AS alert_count
            FROM alert_events
            GROUP BY facility_id
        ) a ON a.facility_id = f.id
        """
    )
    return pd.read_sql(query, _engine())


def train_risk_model() -> None:
    settings = get_settings()
    feature_df = _risk_feature_frame()

    tier_map = {"CORE": 1, "DOWNSTREAM": 2, "SERVICE": 3, "L1": 4, "L2": 5, "L3": 6}
    feature_df["tier_num"] = feature_df["tier_level"].map(tier_map).fillna(0)
    feature_df["latent_risk"] = (
        9.0
        + feature_df["tier_num"] * 4.2
        + feature_df["geo_risk_index"] * 22
        + (100 - feature_df["compliance_score"]) * 0.65
        + feature_df["single_source_dependency"] * 18
        + feature_df["utilization_rate"] * 16
        + feature_df["criticality_index"] * 14
        + (100 - feature_df["avg_reliability"]) * 0.85
        + (1 - feature_df["on_time_rate"]) * 20
        + feature_df["avg_cold_breach"] * 0.08
        + feature_df["critical_alerts"] * 3.2
        - feature_df["traceability_score"] * 4.0
        + np.random.default_rng(20260327).normal(0, 2.8, len(feature_df))
    ).clip(8, 97)

    features = [
        "tier_num",
        "compliance_score",
        "esg_score",
        "single_source_dependency",
        "geo_risk_index",
        "capacity_tonnes_per_week",
        "utilization_rate",
        "criticality_index",
        "inbound_edge_count",
        "avg_reliability",
        "avg_lead_time",
        "avg_cold_breach",
        "on_time_rate",
        "shipment_count",
        "traceability_score",
        "inspection_pass_rate",
        "critical_alerts",
        "alert_count",
    ]
    train_df = feature_df.copy()
    split_idx = max(int(len(train_df) * 0.8), 1)
    x_train = train_df[features].iloc[:split_idx]
    y_train = train_df["latent_risk"].iloc[:split_idx]
    x_valid = train_df[features].iloc[split_idx:]
    y_valid = train_df["latent_risk"].iloc[split_idx:]

    model = XGBRegressor(
        n_estimators=320,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        random_state=20260327,
    )
    model.fit(x_train, y_train)

    train_df["predicted_risk_score"] = model.predict(train_df[features]).clip(0, 100)
    if len(x_valid):
        valid_pred = model.predict(x_valid).clip(0, 100)
        rmse = mean_squared_error(y_valid, valid_pred) ** 0.5
        mae = mean_absolute_error(y_valid, valid_pred)
    else:
        rmse = 0.0
        mae = 0.0

    def root_causes(row: pd.Series) -> dict:
        causes = {}
        if row["geo_risk_index"] > 0.42:
            causes["geo_risk"] = "elevated weather and regional disruption exposure"
        if row["avg_reliability"] < 88:
            causes["supplier_reliability"] = "below-network average fulfilment reliability"
        if row["on_time_rate"] < 0.92:
            causes["transport_execution"] = "late deliveries detected across recent shipments"
        if row["utilization_rate"] > 0.8:
            causes["capacity_pressure"] = "high utilisation limits recovery flexibility"
        if row["traceability_score"] < 0.93:
            causes["traceability_gap"] = "trace completeness has drifted below target"
        if row["critical_alerts"] > 0:
            causes["active_alerts"] = "open critical alerts are still unresolved"
        return causes or {"network_health": "balanced risk posture with monitored volatility"}

    def level(score: float) -> str:
        if score >= 75:
            return "critical"
        if score >= 55:
            return "high"
        if score >= 35:
            return "medium"
        return "low"

    records = []
    assessed_at = datetime.now()
    for row in train_df.to_dict(orient="records"):
        risk_score = round(float(row["predicted_risk_score"]), 2)
        recommended_action = "Increase dual sourcing and reserve cold-chain capacity." if risk_score >= 55 else "Maintain weekly monitoring and buffer coverage."
        records.append(
            {
                "assessment_scope": "facility",
                "entity_id": int(row["facility_id"]),
                "entity_code": row["facility_code"],
                "entity_name": row["facility_name"],
                "tier_level": row["tier_level"],
                "disruption_probability": round(min(0.99, risk_score / 100), 4),
                "risk_score": risk_score,
                "risk_level": level(risk_score),
                "root_causes": root_causes(pd.Series(row)),
                "recommended_action": recommended_action,
                "assessed_at": assessed_at,
            }
        )

    with session_scope() as session:
        session.query(RiskAssessment).delete()
        session.execute(RiskAssessment.__table__.insert(), records)

    joblib.dump(model, settings.artifact_root / "risk_model.joblib")
    _write_json(
        settings.artifact_root / "risk_metrics.json",
        {
            "rmse": round(float(rmse), 4),
            "mae": round(float(mae), 4),
            "facility_count": int(len(train_df)),
            "feature_importance": {feature: round(float(value), 5) for feature, value in zip(features, model.feature_importances_)},
        },
    )


def _demand_frame() -> pd.DataFrame:
    query = text(
        """
        SELECT
            business_date,
            region,
            product_id,
            SUM(units_sold) AS units_sold,
            AVG(price_index) AS price_index,
            AVG(promotion_intensity) AS promotion_intensity,
            AVG(weather_index) AS weather_index,
            AVG(festival_index) AS festival_index
        FROM demand_history
        GROUP BY business_date, region, product_id
        ORDER BY business_date, region, product_id
        """
    )
    return pd.read_sql(query, _engine(), parse_dates=["business_date"])


def train_forecast_model(forecast_horizon: int = 30) -> None:
    settings = get_settings()
    demand_df = _demand_frame()
    demand_df["region_code"] = demand_df["region"].astype("category").cat.codes
    demand_df["product_code"] = demand_df["product_id"].astype("category").cat.codes
    demand_df["day_of_week"] = demand_df["business_date"].dt.dayofweek
    demand_df["month"] = demand_df["business_date"].dt.month
    demand_df["week_of_year"] = demand_df["business_date"].dt.isocalendar().week.astype(int)
    demand_df["is_weekend"] = demand_df["day_of_week"].isin([5, 6]).astype(int)

    demand_df = demand_df.sort_values(["region", "product_id", "business_date"]).reset_index(drop=True)
    grouped = demand_df.groupby(["region", "product_id"], group_keys=False)
    demand_df["lag_1"] = grouped["units_sold"].shift(1)
    demand_df["lag_7"] = grouped["units_sold"].shift(7)
    demand_df["lag_14"] = grouped["units_sold"].shift(14)
    demand_df["rolling_7"] = grouped["units_sold"].transform(lambda s: s.shift(1).rolling(7).mean())
    demand_df["rolling_28"] = grouped["units_sold"].transform(lambda s: s.shift(1).rolling(28).mean())
    demand_df["rolling_std_28"] = grouped["units_sold"].transform(lambda s: s.shift(1).rolling(28).std())

    model_df = demand_df.dropna().copy()
    feature_cols = [
        "region_code",
        "product_code",
        "day_of_week",
        "month",
        "week_of_year",
        "is_weekend",
        "price_index",
        "promotion_intensity",
        "weather_index",
        "festival_index",
        "lag_1",
        "lag_7",
        "lag_14",
        "rolling_7",
        "rolling_28",
        "rolling_std_28",
    ]

    cutoff_date = model_df["business_date"].max() - pd.Timedelta(days=30)
    train_df = model_df[model_df["business_date"] <= cutoff_date]
    valid_df = model_df[model_df["business_date"] > cutoff_date]

    model = XGBRegressor(
        n_estimators=420,
        max_depth=5,
        learning_rate=0.045,
        subsample=0.92,
        colsample_bytree=0.92,
        objective="reg:squarederror",
        random_state=20260327,
    )
    model.fit(train_df[feature_cols], train_df["units_sold"])

    if len(valid_df):
        valid_pred = model.predict(valid_df[feature_cols]).clip(min=0)
        rmse = mean_squared_error(valid_df["units_sold"], valid_pred) ** 0.5
        mae = mean_absolute_error(valid_df["units_sold"], valid_pred)
        mape = float((np.abs(valid_df["units_sold"] - valid_pred) / valid_df["units_sold"].clip(lower=1)).mean())
    else:
        rmse = 0.0
        mae = 0.0
        mape = 0.0

    product_meta = pd.read_sql(text("SELECT id, sku_code, name FROM products"), _engine())
    product_lookup = product_meta.set_index("id").to_dict(orient="index")
    category_maps = {
        "region_code": {region: code for code, region in enumerate(sorted(demand_df["region"].unique()))},
        "product_code": {product_id: code for code, product_id in enumerate(sorted(demand_df["product_id"].unique()))},
    }

    forecast_rows = []
    for (region, product_id), group in demand_df.groupby(["region", "product_id"]):
        history = group.sort_values("business_date").copy()
        units_history = history["units_sold"].tolist()
        last_date = history["business_date"].max().date()
        avg_price = float(history["price_index"].tail(28).mean())
        avg_promo = float(history["promotion_intensity"].tail(28).mean())
        avg_weather = float(history["weather_index"].tail(28).mean())
        avg_festival = float(history["festival_index"].tail(28).mean())

        for step in range(1, forecast_horizon + 1):
            forecast_date = last_date + timedelta(days=step)
            lag_1 = units_history[-1]
            lag_7 = units_history[-7]
            lag_14 = units_history[-14]
            rolling_7 = float(np.mean(units_history[-7:]))
            rolling_28 = float(np.mean(units_history[-28:]))
            rolling_std_28 = float(np.std(units_history[-28:]))
            baseline = rolling_7

            feature_row = pd.DataFrame(
                [
                    {
                        "region_code": history["region_code"].iloc[-1],
                        "product_code": history["product_code"].iloc[-1],
                        "day_of_week": forecast_date.weekday(),
                        "month": forecast_date.month,
                        "week_of_year": forecast_date.isocalendar()[1],
                        "is_weekend": 1 if forecast_date.weekday() >= 5 else 0,
                        "price_index": avg_price,
                        "promotion_intensity": avg_promo,
                        "weather_index": avg_weather,
                        "festival_index": avg_festival,
                        "lag_1": lag_1,
                        "lag_7": lag_7,
                        "lag_14": lag_14,
                        "rolling_7": rolling_7,
                        "rolling_28": rolling_28,
                        "rolling_std_28": rolling_std_28,
                    }
                ]
            )
            prediction = float(model.predict(feature_row)[0])
            prediction = max(0.0, prediction)
            units_history.append(prediction)
            lead_time_days = 4 if product_lookup[product_id]["sku_code"] in {"SKU-TOM-1000", "SKU-VEG-600"} else 6
            safety_stock = 1.65 * max(rolling_std_28, baseline * 0.08) * np.sqrt(lead_time_days)
            reorder_point = prediction * lead_time_days + safety_stock
            uncertainty = max(rolling_std_28 * 1.35, prediction * 0.08)

            forecast_rows.append(
                {
                    "product_id": int(product_id),
                    "region": region,
                    "forecast_date": forecast_date,
                    "baseline_units": round(baseline, 2),
                    "forecast_units": round(prediction, 2),
                    "lower_bound": round(max(0.0, prediction - uncertainty), 2),
                    "upper_bound": round(prediction + uncertainty, 2),
                    "recommended_safety_stock": round(safety_stock, 2),
                    "recommended_reorder_point": round(reorder_point, 2),
                    "model_name": "xgboost_lag_forecast",
                    "generated_at": datetime.now(),
                }
            )

    with session_scope() as session:
        session.query(ForecastResult).delete()
        session.execute(ForecastResult.__table__.insert(), forecast_rows)

    joblib.dump(model, settings.artifact_root / "forecast_model.joblib")
    _write_json(
        settings.artifact_root / "forecast_metrics.json",
        {
            "rmse": round(float(rmse), 4),
            "mae": round(float(mae), 4),
            "mape": round(float(mape), 4),
            "training_rows": int(len(train_df)),
            "validation_rows": int(len(valid_df)),
            "forecast_horizon_days": int(forecast_horizon),
        },
    )
