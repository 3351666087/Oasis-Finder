# Oasis Finder

Oasis Finder is Group 9's fresh-food supply-chain transparency prototype. The current product reframes the project as a merchant-facing method: when a seller displays a product's supply-chain route, stage data, and evidence fields on a product page, users should be more willing to buy because the product feels less risky and more verifiable.

The repository contains a local MySQL digital twin, a PySide6 control tower, risk scoring, demand forecasting, traceability queries, disruption recovery simulation, evidence screenshots, and the final ENT105TC presentation assets.

## Product Premise

Oasis Finder is not only a dashboard. It is a way for merchants to advertise with inspectable evidence:

- Start from a retail-style product shelf with product name, category, price, storage band, latest batch, and proof score.
- Let users click a product and inspect that exact SKU's supplier lots, production batch, cold-chain route, retail shelf state, and quality checkpoints.
- Preserve the full operational dashboard and mesh topology for managers, but make the home page consumer-friendly for marketing use.
- Present concrete values such as time, place, batch, quality, temperature, shipment, and risk.
- Keep the code and interface open for review while making merchant data responsibility explicit.

## CP Group Pilot Fit

Oasis Finder is especially suitable for a CP Group-style partner because CP Group publicly describes a broad business portfolio across Agro-industry and Food, Retail and Distribution, E-Commerce and Digital, and other business lines. Its food business is described as a fully integrated value chain covering feed, livestock farming, food production, retail stores, and restaurants, with technology used for full traceability across production. CPF also describes its business as Feed, Farm, and Food, and CP Axtra connects Makro and Lotus's retail/wholesale channels with fresh and frozen meat, vegetables, and fruits.

This makes CP Group a strong pilot case: a single product card can connect upstream farm/feed inputs, processing plants, cold-chain shipments, and retail shelves. The product is not CP-only, though. Any merchant can use the same schema if it can provide SKU, batch, supplier lot, facility, shipment, inspection, QR, IoT, and audit evidence fields.

Reference links:

- CP Group business lines and traceability: https://www.cpgroupglobal.com/en/about-cp-group/our-business
- CPF business overview: https://www.cpfworldwide.com/en/about
- CP Axtra retail/wholesale fresh-food context: https://www.cpaxtra.com/en/newsroom/news/548/makro-expands-own-brand-portfolio-products-to-elevate-customer-experience-and-cement-position-as-a-leading-food-destination

## Data Responsibility

This project open-sources the interface, schema, and evidence workflow. It does not guarantee the authenticity of data submitted by a merchant, supplier, logistics provider, or large enterprise.

In production, the following evidence should be validated by supplier records, QR events, IoT logs, and third-party audits:

- Product identity: SKU, GTIN, QR code, batch ID, lot ID.
- Critical tracking event: harvest, production, receiving, shipping, arrival, transformation.
- Location: supplier, plant, warehouse, retail node, GLN or equivalent location code.
- Time: event timestamp, production date, expiry date, dispatch time, arrival time.
- Condition: temperature range, breach minutes, freshness index, shelf-life state.
- Quality proof: inspection result, package score, pathogen or residue checks.
- Evidence owner: supplier, carrier, auditor, certificate URI, evidence hash, or signed file reference.

These fields follow the spirit of FDA FSMA 204 Critical Tracking Events / Key Data Elements and GS1 traceability standards.

## Current Capabilities

- Models a multi-tier fresh-food supply network across L1, L2, L3, core plants, downstream nodes, and service providers.
- Adds a product-first home tab where merchants can show product names and categories before users inspect a SKU-level supply route.
- Traces product batches back to supplier lots, inspections, material usage, and shipment legs.
- Adds a clickable Network Mesh detail panel that exposes stage-level node data after selecting a facility.
- Trains XGBoost-based risk and demand forecasting models.
- Simulates disruption recovery with OR-Tools allocation logic.
- Provides a PySide6 desktop application with Product Shelf, Dashboard, Network Mesh, Traceability, Forecasting, and Scenario Lab tabs.
- Generates report assets, UI screenshots, speaker scripts, and presentation evidence for coursework demonstration.

## Runtime Evidence Snapshot

The latest validated local runtime contains:

| Evidence area | Current value |
| --- | ---: |
| Organizations | 79 |
| Facilities | 97 |
| Active supply links | 200 |
| Supplier lots | 154 |
| Finished-goods batches | 418 |
| Shipments | 746 |
| Demand observations | 35,040 |
| Risk model RMSE | 5.83 |
| Risk model MAE | 4.65 |
| Forecast MAPE | 4.81% |
| Forecast horizon | 30 days |

## Repository Structure

```text
.
|-- app.py                         # Desktop app entry point
|-- manage.py                      # Bootstrap, training, reporting, and health commands
|-- environment.yml                # Conda environment definition
|-- requirements.txt               # Pip dependency list
|-- scripts/
|   |-- setup_local_mysql.ps1      # Local MySQL runtime setup
|   `-- build_inf_docx.py          # Technical report generator
|-- src/mesh_supply_chain/
|   |-- models.py                  # SQLAlchemy schema
|   |-- seed.py                    # Synthetic digital-twin data generation
|   |-- analytics.py               # Risk and forecast training
|   |-- services.py                # Query, node-detail, and scenario service layer
|   |-- health.py                  # End-to-end runtime health checks
|   `-- ui.py                      # PySide6 interface
|-- artifacts/
|   |-- report_assets/             # Exported report figures
|   `-- ui_captures_native/        # Demonstration screenshots, including product_shelf_cp_route.png
`-- outputs/
    `-- oasis-finder-group9-ent105tc-rebuild-v2/
        |-- output.pptx
        |-- chart_data/
        |-- speaker_script_rebuild_v2_Rui_Zixiu.md
        `-- speaker_script_rebuild_v2_Rui_Zixiu.pdf
```

## Quick Start

Create and activate the environment:

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

## Final Presentation

The rebuilt ENT105TC deck is available at:

```text
outputs/oasis-finder-group9-ent105tc-rebuild-v2/output.pptx
```

The deck includes the reframed questionnaire logic, CSV-backed charts, merchant value argument, clickable node-detail product proof, GitHub/open-source evidence, merchant A/B test validation plan, and APA-style source links.
