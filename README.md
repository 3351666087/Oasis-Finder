# Oasis Finder

Oasis Finder is a fresh-food supply chain intelligence prototype for Group 9. It combines a local MySQL digital twin, a PySide6 operations interface, risk scoring, demand forecasting, traceability queries, and disruption recovery simulation.

The project was built for the ENT105TC / INF coursework storyline: move beyond superficial transparency and provide verifiable, decision-grade supply chain evidence.

## What It Does

- Models a multi-tier fresh-food supply network across L1, L2, L3, core plants, downstream nodes, and service providers.
- Traces finished product batches back to supplier lots, inspections, material usage, and shipment legs.
- Trains XGBoost-based risk and demand forecasting models.
- Simulates disruption recovery with OR-Tools allocation logic.
- Provides a PySide6 desktop control tower with Dashboard, Network Mesh, Traceability, Forecasting, and Scenario Lab tabs.
- Generates report assets and presentation evidence for coursework demonstration.

## Current Evidence Snapshot

The latest seeded runtime used for the presentation contains:

| Evidence area | Current value |
| --- | ---: |
| Organisations | 79 |
| Facilities | 97 |
| Active supply links | 200 |
| Supplier lots | 154 |
| Finished-goods batches | 418 |
| Shipments | 746 |
| Demand observations | 35,040 |
| Risk model RMSE | 5.83 |
| Forecast MAPE | 4.81% |
| Forecast horizon | 30 days |

## Repository Structure

```text
.
├── app.py                         # Desktop app entry point
├── manage.py                      # Bootstrap, training, reporting, and health commands
├── environment.yml                # Conda environment definition
├── requirements.txt               # Pip dependency list
├── scripts/
│   ├── setup_local_mysql.ps1      # Local MySQL runtime setup
│   └── build_inf_docx.py          # Technical report generator
├── src/mesh_supply_chain/
│   ├── models.py                  # SQLAlchemy schema
│   ├── seed.py                    # Synthetic digital-twin data generation
│   ├── analytics.py               # Risk and forecast training
│   ├── services.py                # Query and scenario service layer
│   ├── health.py                  # End-to-end runtime health checks
│   └── ui.py                      # PySide6 interface
└── artifacts/
    ├── report_assets/             # Exported report figures
    └── ui_captures_native/        # Demonstration screenshots
```

## Quick Start

Create the environment:

```powershell
conda env create -f environment.yml
conda activate mesh_supply_chain
```

Prepare the local MySQL runtime:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_local_mysql.ps1
```

Build the database, seed data, train models, and generate the report:

```powershell
python .\manage.py bootstrap-all --drop-existing
```

Run the health check:

```powershell
python .\manage.py health-check
```

Start the desktop application:

```powershell
python .\app.py
```

## Engineering Notes

- Database URLs are created with SQLAlchemy `URL.create`, so passwords with special characters such as `#` are handled safely.
- Engines use `pool_pre_ping`, connection timeout, and pool recycling to improve local demo reliability.
- The `health-check` command validates database connectivity, table scale, dashboard services, traceability flow, forecasting flow, scenario simulation, and evidence artifacts.
- Runtime state, local credentials, caches, temporary previews, and heavy model binaries are intentionally excluded from GitHub.

## Presentation

The polished ENT105TC presentation deck is available in:

```text
outputs/oasis-finder-group9-ent105tc-final/output.pptx
```

After publishing, the first slide contains the GitHub repository link and the deck includes a browser screenshot of the repository page.
