from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mesh_supply_chain.analytics import train_forecast_model, train_risk_model
from mesh_supply_chain.bootstrap import bootstrap_database
from mesh_supply_chain.health import format_health_report, run_health_check
from mesh_supply_chain.reports import build_presubmission_report
from mesh_supply_chain.seed import seed_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mesh Supply Chain system manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subparsers.add_parser("bootstrap-db", help="Create database and tables")
    bootstrap_parser.add_argument("--drop-existing", action="store_true")

    seed_parser = subparsers.add_parser("seed", help="Seed synthetic supply chain data")
    seed_parser.add_argument("--drop-existing", action="store_true")

    train_parser = subparsers.add_parser("train", help="Train analytics artifacts")
    train_parser.add_argument("--forecast-horizon", type=int, default=30)

    report_parser = subparsers.add_parser("report", help="Generate the pre-submission report")
    report_parser.add_argument("--output", default="artifacts/INF101TC_PreSubmission_Report.docx")

    health_parser = subparsers.add_parser("health-check", help="Run an end-to-end runtime health check")
    health_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    bootstrap_all = subparsers.add_parser("bootstrap-all", help="Bootstrap database, seed data, train models, and build report")
    bootstrap_all.add_argument("--drop-existing", action="store_true")
    bootstrap_all.add_argument("--forecast-horizon", type=int, default=30)
    bootstrap_all.add_argument("--report-output", default="artifacts/INF101TC_PreSubmission_Report.docx")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "bootstrap-db":
        bootstrap_database(drop_existing=args.drop_existing)
        return

    if args.command == "seed":
        bootstrap_database(drop_existing=args.drop_existing)
        seed_database()
        return

    if args.command == "train":
        train_risk_model()
        train_forecast_model(forecast_horizon=args.forecast_horizon)
        return

    if args.command == "report":
        build_presubmission_report(Path(args.output))
        return

    if args.command == "health-check":
        payload = run_health_check()
        if args.json:
            import json

            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(format_health_report(payload))
        if payload["status"] != "pass":
            raise SystemExit(1)
        return

    if args.command == "bootstrap-all":
        bootstrap_database(drop_existing=args.drop_existing)
        seed_database()
        train_risk_model()
        train_forecast_model(forecast_horizon=args.forecast_horizon)
        build_presubmission_report(Path(args.report_output))
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()
