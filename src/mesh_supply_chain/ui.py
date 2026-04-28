from __future__ import annotations

import sys

import networkx as nx
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .services import (
    DashboardSnapshot,
    get_batch_codes,
    get_batch_trace,
    get_disruptable_facilities,
    get_facility_node_detail,
    get_product_journey,
    get_forecast_series,
    get_product_options,
    get_region_options,
    load_dashboard_snapshot,
    load_network_data,
    load_product_shelf,
    simulate_disruption,
)


class DataFrameModel(QAbstractTableModel):
    def __init__(self, frame: pd.DataFrame | None = None):
        super().__init__()
        self._frame = frame if frame is not None else pd.DataFrame()

    def set_frame(self, frame: pd.DataFrame) -> None:
        self.beginResetModel()
        self._frame = frame.copy()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._frame)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._frame.columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.TextAlignmentRole):
            return None
        value = self._frame.iloc[index.row(), index.column()]
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:,.2f}"
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M") if hasattr(value, "hour") else value.strftime("%Y-%m-%d")
        return str(value)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._frame.columns[section]).replace("_", " ").title()
        return str(section + 1)


class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self):
        figure = Figure(figsize=(5.2, 3.2), facecolor="#F6F3EA")
        self.ax = figure.add_subplot(111)
        super().__init__(figure)
        self.setStyleSheet("background: transparent;")


class KpiCard(QFrame):
    def __init__(self, title: str, accent: str):
        super().__init__()
        self.setObjectName("kpiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("kpiTitle")
        self.value_label = QLabel("--")
        self.value_label.setObjectName("kpiValue")
        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("kpiSubtitle")
        self.value_label.setStyleSheet(f"color: {accent};")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)

    def update_value(self, value: str, subtitle: str) -> None:
        self.value_label.setText(value)
        self.subtitle_label.setText(subtitle)


def create_table() -> tuple[QTableView, DataFrameModel]:
    table = QTableView()
    model = DataFrameModel()
    table.setModel(model)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setSelectionMode(QTableView.NoSelection)
    table.setEditTriggers(QTableView.NoEditTriggers)
    table.setMinimumHeight(220)
    return table, model


class ProductShelfTab(QWidget):
    def __init__(self):
        super().__init__()
        self._shelf_frame = pd.DataFrame()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(18)

        hero_copy = QVBoxLayout()
        title = QLabel("Oasis Finder Product Shelf")
        title.setObjectName("heroTitle")
        subtitle = QLabel(
            "A consumer-facing transparency layer: shoppers see the product first, then click into the batch route, supplier lots, cold-chain legs, and quality evidence."
        )
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)
        cp_note = QLabel(
            "CP Group fit: integrated food and retail operations can connect Feed/Farm/Food data to Makro, Lotus's, 7-Eleven, or partner shelves. The same schema also works for any merchant with SKU, lot, facility, shipment, inspection, and IoT records."
        )
        cp_note.setObjectName("heroNote")
        cp_note.setWordWrap(True)
        hero_copy.addWidget(title)
        hero_copy.addWidget(subtitle)
        hero_copy.addWidget(cp_note)
        hero_layout.addLayout(hero_copy, 3)

        self.signal_cards = [
            KpiCard("Traceable SKUs", "#006D77"),
            KpiCard("Avg Proof Score", "#1F6F8B"),
            KpiCard("Cold-Chain Legs", "#D97706"),
            KpiCard("Merchant Use", "#8B5E34"),
        ]
        signal_grid = QGridLayout()
        signal_grid.setSpacing(10)
        for idx, card in enumerate(self.signal_cards):
            signal_grid.addWidget(card, idx // 2, idx % 2)
        hero_layout.addLayout(signal_grid, 2)
        layout.addWidget(hero)

        main_splitter = QSplitter(Qt.Vertical)
        top_splitter = QSplitter(Qt.Horizontal)

        shelf_panel = QWidget()
        shelf_layout = QVBoxLayout(shelf_panel)
        shelf_layout.setContentsMargins(0, 0, 0, 0)
        shelf_header = QHBoxLayout()
        shelf_label = QLabel("Retail-Style Product Shelf")
        shelf_label.setObjectName("sectionTitle")
        refresh_button = QPushButton("Refresh Products")
        refresh_button.clicked.connect(self.refresh)
        shelf_header.addWidget(shelf_label)
        shelf_header.addStretch(1)
        shelf_header.addWidget(refresh_button)
        shelf_layout.addLayout(shelf_header)
        self.product_table, self.product_model = create_table()
        self.product_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.product_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.product_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.product_table.horizontalHeader().setStretchLastSection(True)
        self.product_table.selectionModel().selectionChanged.connect(self._handle_product_selection)
        self.product_table.setMinimumHeight(330)
        shelf_layout.addWidget(self.product_table)
        top_splitter.addWidget(shelf_panel)

        route_panel = QWidget()
        route_layout = QVBoxLayout(route_panel)
        route_layout.setContentsMargins(0, 0, 0, 0)
        route_label = QLabel("Clicked Product Supply Route")
        route_label.setObjectName("sectionTitle")
        route_layout.addWidget(route_label)
        self.route_canvas = PlotCanvas()
        self.route_canvas.setMinimumHeight(170)
        route_layout.addWidget(self.route_canvas, 3)
        self.product_box = QGroupBox("Selected Product Proof")
        product_form = QFormLayout(self.product_box)
        self.product_labels = {
            key: QLabel("--")
            for key in ["product", "category", "batch", "route"]
        }
        for label in self.product_labels.values():
            label.setWordWrap(True)
        product_form.addRow("Product", self.product_labels["product"])
        product_form.addRow("Category", self.product_labels["category"])
        product_form.addRow("Batch", self.product_labels["batch"])
        product_form.addRow("Route", self.product_labels["route"])
        route_layout.addWidget(self.product_box, 2)
        top_splitter.addWidget(route_panel)
        top_splitter.setSizes([780, 660])
        main_splitter.addWidget(top_splitter)

        bottom_splitter = QSplitter(Qt.Horizontal)
        node_panel = QWidget()
        node_layout = QVBoxLayout(node_panel)
        node_layout.setContentsMargins(0, 0, 0, 0)
        node_title = QLabel("Route Node Variables")
        node_title.setObjectName("sectionTitle")
        node_layout.addWidget(node_title)
        self.route_nodes_table, self.route_nodes_model = create_table()
        self.route_nodes_table.setMinimumHeight(230)
        node_layout.addWidget(self.route_nodes_table)
        bottom_splitter.addWidget(node_panel)

        evidence_panel = QWidget()
        evidence_layout = QVBoxLayout(evidence_panel)
        evidence_layout.setContentsMargins(0, 0, 0, 0)
        evidence_title = QLabel("Evidence Fields Visible After Product Click")
        evidence_title.setObjectName("sectionTitle")
        evidence_layout.addWidget(evidence_title)
        self.evidence_table, self.evidence_model = create_table()
        self.evidence_table.setMinimumHeight(230)
        evidence_layout.addWidget(self.evidence_table)
        bottom_splitter.addWidget(evidence_panel)
        bottom_splitter.setSizes([520, 920])
        main_splitter.addWidget(bottom_splitter)
        main_splitter.setSizes([640, 240])
        layout.addWidget(main_splitter)

    def refresh(self) -> None:
        self._shelf_frame = load_product_shelf()
        if self._shelf_frame.empty:
            self.product_model.set_frame(pd.DataFrame())
            self.route_nodes_model.set_frame(pd.DataFrame())
            self.evidence_model.set_frame(pd.DataFrame())
            self._draw_empty_route("No product data")
            return

        display_columns = [
            "product_name",
            "category_label",
            "unit_price",
            "proof_score",
            "consumer_claim",
        ]
        self.product_model.set_frame(self._shelf_frame[display_columns].copy())
        for column_idx, width in enumerate([260, 180, 80, 90, 210]):
            self.product_table.setColumnWidth(column_idx, width)

        avg_proof = float(self._shelf_frame["proof_score"].mean())
        cold_legs = int(self._shelf_frame["shipment_legs"].sum())
        traceable = int(len(self._shelf_frame))
        cp_categories = ", ".join(sorted(self._shelf_frame["category_label"].unique())[:4])
        self.signal_cards[0].update_value(str(traceable), "Retail product cards with batch-level routes")
        self.signal_cards[1].update_value(f"{avg_proof:.1f}", "Quality + traceability + delivery score")
        self.signal_cards[2].update_value(str(cold_legs), "Shipment legs attached to latest batches")
        self.signal_cards[3].update_value("Ad Proof", f"Works for CP Group and non-CP merchants: {cp_categories}")

        self.product_table.selectRow(0)
        self._show_product(str(self._shelf_frame.iloc[0]["sku_code"]))

    def _handle_product_selection(self) -> None:
        selected = self.product_table.selectionModel().selectedRows()
        if not selected or self._shelf_frame.empty:
            return
        row_idx = selected[0].row()
        if 0 <= row_idx < len(self._shelf_frame):
            self._show_product(str(self._shelf_frame.iloc[row_idx]["sku_code"]))

    def _show_product(self, sku_code: str) -> None:
        journey = get_product_journey(sku_code)
        overview = journey["overview"]
        route_nodes = journey["route_nodes"]
        route_edges = journey["route_edges"]
        evidence = journey["evidence"]

        price = float(overview["unit_price"])
        margin_rate = float(overview["margin_rate"] or 0)
        traceability_score = float(overview.get("traceability_score") or 0)
        self.product_labels["product"].setText(
            f"{overview['sku_code']} | {overview['product_name']} | RMB {price:.2f} | margin {margin_rate:.1f}%"
        )
        self.product_labels["category"].setText(
            f"{overview['category']} | shelf life {overview['shelf_life_days']} days | storage {overview['storage_temp_band']}"
        )
        self.product_labels["batch"].setText(
            f"{overview['batch_code']} | {overview['production_date']:%Y-%m-%d} -> "
            f"{overview['expiry_date']:%Y-%m-%d} | Q {float(overview['quality_score']):.1f} | trace {traceability_score:.1f}%"
        )
        self.product_labels["route"].setText(
            f"{overview['route_node_count']} nodes | {overview['route_edge_count']} flows | "
            f"{overview['supplier_lot_count']} supplier lots | {overview['shipment_leg_count']} cold-chain legs"
        )
        self.route_nodes_model.set_frame(route_nodes)
        self.evidence_model.set_frame(evidence)
        self._draw_product_route(sku_code, route_nodes, route_edges)

    def _draw_empty_route(self, message: str) -> None:
        ax = self.route_canvas.ax
        ax.clear()
        ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12, color="#5F6C72")
        ax.axis("off")
        self.route_canvas.draw()

    def _draw_product_route(self, sku_code: str, route_nodes: pd.DataFrame, route_edges: pd.DataFrame) -> None:
        if route_nodes.empty:
            self._draw_empty_route("No route available for selected product")
            return

        graph = nx.DiGraph()
        for _, row in route_nodes.iterrows():
            graph.add_node(
                row["facility_code"],
                stage=row["stage"],
                stage_order=int(row["stage_order"]),
                label=row["facility_code"],
            )
        for _, row in route_edges.iterrows():
            graph.add_edge(row["from_code"], row["to_code"], label=row["flow"])

        positions: dict[str, tuple[float, float]] = {}
        for stage_order, group in route_nodes.groupby("stage_order", sort=True):
            count = len(group)
            for idx, (_, row) in enumerate(group.iterrows()):
                y = (count - 1) / 2 - idx
                positions[row["facility_code"]] = (float(stage_order), y)

        stage_colors = {
            "Ingredient source": "#2A9D8F",
            "Processing / packing": "#1F6F8B",
            "Distribution center": "#D97706",
            "Retail shelf": "#AD5D4E",
            "Logistics node": "#8D99AE",
        }
        node_colors = [stage_colors.get(graph.nodes[node]["stage"], "#8D99AE") for node in graph.nodes]

        ax = self.route_canvas.ax
        ax.clear()
        nx.draw_networkx_edges(
            graph,
            positions,
            ax=ax,
            arrows=True,
            arrowsize=14,
            edge_color="#6C757D",
            alpha=0.42,
            width=1.2,
            connectionstyle="arc3,rad=0.03",
        )
        nx.draw_networkx_nodes(
            graph,
            positions,
            ax=ax,
            node_color=node_colors,
            node_size=820,
            linewidths=1.2,
            edgecolors="#FFFFFF",
        )
        nx.draw_networkx_labels(graph, positions, labels={node: node for node in graph.nodes}, font_size=7, font_weight="bold", ax=ax)
        y_values = [position[1] for position in positions.values()]
        label_y = min(y_values) - 0.45 if y_values else -0.8
        ax.set_ylim(label_y - 0.45, (max(y_values) + 0.55) if y_values else 1.0)
        stage_labels = route_nodes[["stage_order", "stage"]].drop_duplicates().sort_values("stage_order")
        for _, row in stage_labels.iterrows():
            ax.text(
                float(row["stage_order"]),
                label_y,
                row["stage"],
                ha="center",
                va="top",
                fontsize=8,
                fontweight="bold",
                color="#12343B",
            )
        ax.axis("off")
        self.route_canvas.draw()


class DashboardTab(QWidget):
    def __init__(self):
        super().__init__()
        self.cards = [
            KpiCard("Supplier Facilities", "#1F6F8B"),
            KpiCard("Active Links", "#3AA17E"),
            KpiCard("Batches", "#D97706"),
            KpiCard("On-Time Rate", "#AD5D4E"),
            KpiCard("Average Risk", "#7B2CBF"),
            KpiCard("Active Alerts", "#B22222"),
        ]

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        card_row = QGridLayout()
        for idx, card in enumerate(self.cards):
            card_row.addWidget(card, idx // 3, idx % 3)
        layout.addLayout(card_row)

        chart_row = QHBoxLayout()
        self.risk_canvas = PlotCanvas()
        self.demand_canvas = PlotCanvas()
        chart_row.addWidget(self.risk_canvas, 1)
        chart_row.addWidget(self.demand_canvas, 1)
        layout.addLayout(chart_row)

        self.table, self.table_model = create_table()
        layout.addWidget(QLabel("Top Risk Entities"))
        layout.addWidget(self.table)

    def refresh(self) -> None:
        snapshot: DashboardSnapshot = load_dashboard_snapshot()
        self.cards[0].update_value(str(snapshot.kpis["supplier_facilities"]), "L1/L2/L3 facilities inside the mesh")
        self.cards[1].update_value(str(snapshot.kpis["active_links"]), "Active material and distribution links")
        self.cards[2].update_value(str(snapshot.kpis["total_batches"]), "Traceable finished-goods batches")
        self.cards[3].update_value(f"{snapshot.kpis['on_time_rate']:.2f}%", "Shipment execution performance")
        self.cards[4].update_value(f"{snapshot.kpis['average_risk_score']:.1f}", "Average predicted disruption risk")
        self.cards[5].update_value(str(snapshot.kpis["active_alerts"]), "Open or mitigating alert events")

        risk_ax = self.risk_canvas.ax
        risk_ax.clear()
        risk_plot = snapshot.risk_distribution.groupby("tier_level", as_index=False)["avg_score"].mean()
        risk_ax.bar(risk_plot["tier_level"], risk_plot["avg_score"], color=["#2A9D8F", "#1D3557", "#E76F51", "#264653", "#F4A261", "#8D99AE"])
        risk_ax.set_title("Average Risk by Tier", fontsize=11)
        risk_ax.set_ylabel("Risk Score")
        self.risk_canvas.draw()

        demand_ax = self.demand_canvas.ax
        demand_ax.clear()
        demand_ax.plot(snapshot.demand_trend["business_date"], snapshot.demand_trend["units_sold"], color="#1F6F8B", linewidth=2.2)
        demand_ax.fill_between(snapshot.demand_trend["business_date"], snapshot.demand_trend["units_sold"], color="#99C1DE", alpha=0.35)
        demand_ax.set_title("Demand Trend - Last 60 Days", fontsize=11)
        demand_ax.tick_params(axis="x", rotation=25)
        self.demand_canvas.draw()

        self.table_model.set_frame(snapshot.top_risks)


class NetworkTab(QWidget):
    def __init__(self):
        super().__init__()
        self._node_codes: list[str] = []
        self._node_collection = None

        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.tier_combo = QComboBox()
        self.tier_combo.addItems(["ALL", "L1", "L2", "L3", "CORE", "DOWNSTREAM", "SERVICE"])
        refresh_button = QPushButton("Refresh Topology")
        refresh_button.clicked.connect(self.refresh)
        self.summary_label = QLabel("Mesh topology view")
        controls.addWidget(QLabel("Tier Filter"))
        controls.addWidget(self.tier_combo)
        controls.addWidget(refresh_button)
        controls.addStretch(1)
        controls.addWidget(self.summary_label)
        layout.addLayout(controls)

        splitter = QSplitter(Qt.Vertical)
        top_splitter = QSplitter(Qt.Horizontal)
        plot_panel = QWidget()
        plot_layout = QVBoxLayout(plot_panel)
        self.canvas = PlotCanvas()
        self.canvas.mpl_connect("pick_event", self._handle_node_pick)
        plot_layout.addWidget(self.canvas)
        top_splitter.addWidget(plot_panel)

        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)
        self.detail_box = QGroupBox("Clicked Node Detail")
        detail_form = QFormLayout(self.detail_box)
        self.detail_labels = {
            key: QLabel("--")
            for key in [
                "identity",
                "location",
                "organization",
                "capacity",
                "risk",
                "links",
                "responsibility",
            ]
        }
        for label in self.detail_labels.values():
            label.setWordWrap(True)
        detail_form.addRow("Node", self.detail_labels["identity"])
        detail_form.addRow("Location", self.detail_labels["location"])
        detail_form.addRow("Operator", self.detail_labels["organization"])
        detail_form.addRow("Capacity", self.detail_labels["capacity"])
        detail_form.addRow("Risk", self.detail_labels["risk"])
        detail_form.addRow("Evidence", self.detail_labels["links"])
        detail_form.addRow("Data Note", self.detail_labels["responsibility"])
        detail_layout.addWidget(self.detail_box)

        detail_layout.addWidget(QLabel("Supply-Stage Variables Displayed After Node Click"))
        self.stage_table, self.stage_model = create_table()
        self.stage_table.setMinimumHeight(260)
        detail_layout.addWidget(self.stage_table)
        top_splitter.addWidget(detail_panel)
        top_splitter.setSizes([700, 620])
        splitter.addWidget(top_splitter)

        self.table, self.table_model = create_table()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.selectionModel().selectionChanged.connect(self._handle_table_selection)
        splitter.addWidget(self.table)
        splitter.setSizes([520, 220])
        layout.addWidget(splitter)

    def refresh(self) -> None:
        nodes, edges = load_network_data(self.tier_combo.currentText())
        graph = nx.DiGraph()
        for _, node in nodes.iterrows():
            graph.add_node(node["facility_code"], name=node["name"], tier=node["tier_level"], risk=node["risk_score"])
        for _, edge in edges.iterrows():
            graph.add_edge(edge["from_code"], edge["to_code"], label=edge["material_name"] or edge["product_name"] or edge["relation_type"], tier=edge["tier_level"])

        tier_order = {"L3": 0, "L2": 1, "L1": 2, "CORE": 3, "DOWNSTREAM": 4, "SERVICE": 5}
        grouped_nodes = {}
        for node, data in graph.nodes(data=True):
            grouped_nodes.setdefault(data["tier"], []).append(node)

        positions = {}
        for tier, tier_nodes in grouped_nodes.items():
            x = tier_order.get(tier, 6)
            for idx, node in enumerate(tier_nodes):
                positions[node] = (x, -idx)

        colors = {"L1": "#2A9D8F", "L2": "#1D3557", "L3": "#E76F51", "CORE": "#264653", "DOWNSTREAM": "#F4A261", "SERVICE": "#8D99AE"}
        ax = self.canvas.ax
        ax.clear()
        nx.draw_networkx_edges(graph, positions, ax=ax, arrows=True, arrowsize=10, edge_color="#6C757D", alpha=0.25, width=0.8)
        self._node_codes = list(graph.nodes)
        self._node_collection = nx.draw_networkx_nodes(
            graph,
            positions,
            ax=ax,
            nodelist=self._node_codes,
            node_color=[colors.get(graph.nodes[n]["tier"], "#ADB5BD") for n in self._node_codes],
            node_size=320,
            linewidths=0.8,
            edgecolors="#FFFFFF",
        )
        self._node_collection.set_picker(8)
        label_subset = {node: node for node in list(graph.nodes)[:48]}
        nx.draw_networkx_labels(graph, positions, labels=label_subset, font_size=6, ax=ax)
        ax.set_title("Clickable Mesh Topology - click a node to inspect supply-stage data", fontsize=11)
        ax.axis("off")
        self.canvas.draw()
        self.summary_label.setText(f"{len(nodes)} nodes | {len(edges)} links")
        self.table_model.set_frame(nodes[["facility_code", "name", "tier_level", "facility_type", "region", "city", "risk_score"]].copy())
        if self._node_codes:
            self._show_node_detail(self._node_codes[0])

    def _handle_node_pick(self, event) -> None:
        if event.artist is not self._node_collection or not len(event.ind):
            return
        node_idx = int(event.ind[0])
        if 0 <= node_idx < len(self._node_codes):
            self._show_node_detail(self._node_codes[node_idx])

    def _handle_table_selection(self) -> None:
        selected = self.table.selectionModel().selectedRows()
        if not selected or self.table_model._frame.empty:
            return
        row_idx = selected[0].row()
        if 0 <= row_idx < len(self.table_model._frame):
            self._show_node_detail(str(self.table_model._frame.iloc[row_idx]["facility_code"]))

    def _show_node_detail(self, facility_code: str) -> None:
        detail = get_facility_node_detail(facility_code)
        overview = detail["overview"]
        self.detail_labels["identity"].setText(
            f"{overview['facility_code']} | {overview['name']} | {overview['tier_level']} / {overview['facility_type']}"
        )
        self.detail_labels["location"].setText(
            f"{overview['country']} - {overview['province']} - {overview['city']} - {overview['district']} "
            f"({overview['latitude']:.3f}, {overview['longitude']:.3f})"
        )
        self.detail_labels["organization"].setText(
            f"{overview['organization_name']} | compliance {overview['compliance_score']:.1f} | ESG {overview['esg_score']:.1f}"
        )
        self.detail_labels["capacity"].setText(
            f"{overview['capacity_tonnes_per_week']:.1f} t/week | utilization {overview['utilization_rate'] * 100:.1f}% | "
            f"cold chain: {overview['cold_chain_level']}"
        )
        self.detail_labels["risk"].setText(
            f"{overview['risk_level']} | score {overview['risk_score']:.1f} | "
            f"disruption probability {overview['disruption_probability'] * 100:.1f}%"
        )
        self.detail_labels["links"].setText(
            f"{overview['inbound_links']} inbound links | {overview['outbound_links']} outbound links | "
            f"{overview['supplier_lots']} supplier lots | {overview['product_batches']} batches | "
            f"{overview['shipments']} shipments | {overview['active_alerts']} active alerts"
        )
        self.detail_labels["responsibility"].setText(
            "Open-source interface and schema only. Merchant-submitted values should be validated by supplier records, QR events, IoT logs, and third-party audits."
        )
        self.stage_model.set_frame(detail["stages"])


class TraceabilityTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.batch_combo = QComboBox()
        self.batch_combo.setMinimumWidth(220)
        self.load_button = QPushButton("Load Trace")
        self.load_button.clicked.connect(self.refresh)
        controls.addWidget(QLabel("Batch"))
        controls.addWidget(self.batch_combo)
        controls.addWidget(self.load_button)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.header_box = QGroupBox("Batch Overview")
        self.header_form = QFormLayout(self.header_box)
        self.header_labels = {key: QLabel("--") for key in ["product", "sku", "plant", "production", "expiry", "quantity", "quality"]}
        self.header_form.addRow("Product", self.header_labels["product"])
        self.header_form.addRow("SKU", self.header_labels["sku"])
        self.header_form.addRow("Plant", self.header_labels["plant"])
        self.header_form.addRow("Production Date", self.header_labels["production"])
        self.header_form.addRow("Expiry Date", self.header_labels["expiry"])
        self.header_form.addRow("Batch Qty", self.header_labels["quantity"])
        self.header_form.addRow("Quality Score", self.header_labels["quality"])
        layout.addWidget(self.header_box)

        splitter = QSplitter(Qt.Vertical)
        self.components_table, self.components_model = create_table()
        self.shipments_table, self.shipments_model = create_table()
        splitter.addWidget(self.components_table)
        splitter.addWidget(self.shipments_table)
        splitter.setSizes([250, 250])
        layout.addWidget(splitter)

        self.reload_batches()

    def reload_batches(self) -> None:
        self.batch_combo.clear()
        self.batch_combo.addItems(get_batch_codes())

    def refresh(self) -> None:
        trace = get_batch_trace(self.batch_combo.currentText())
        header = trace["header"]
        self.header_labels["product"].setText(str(header["product_name"]))
        self.header_labels["sku"].setText(str(header["sku_code"]))
        self.header_labels["plant"].setText(str(header["plant_name"]))
        self.header_labels["production"].setText(header["production_date"].strftime("%Y-%m-%d"))
        self.header_labels["expiry"].setText(header["expiry_date"].strftime("%Y-%m-%d"))
        self.header_labels["quantity"].setText(f"{header['actual_qty']:.2f}")
        self.header_labels["quality"].setText(f"{header['quality_score']:.2f}")
        self.components_model.set_frame(trace["components"])
        self.shipments_model.set_frame(trace["shipments"])


class ForecastTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.product_combo = QComboBox()
        self.region_combo = QComboBox()
        self.refresh_button = QPushButton("Refresh Forecast")
        self.refresh_button.clicked.connect(self.refresh)
        for sku_code, name in get_product_options():
            self.product_combo.addItem(f"{sku_code} | {name}", sku_code)
        self.region_combo.addItems(get_region_options())
        controls.addWidget(QLabel("Product"))
        controls.addWidget(self.product_combo, 2)
        controls.addWidget(QLabel("Region"))
        controls.addWidget(self.region_combo, 1)
        controls.addWidget(self.refresh_button)
        layout.addLayout(controls)

        self.summary = QLabel("Forecast summary")
        layout.addWidget(self.summary)

        self.canvas = PlotCanvas()
        layout.addWidget(self.canvas)

        self.table, self.table_model = create_table()
        layout.addWidget(self.table)

    def refresh(self) -> None:
        sku_code = self.product_combo.currentData()
        region = self.region_combo.currentText()
        series = get_forecast_series(sku_code, region)
        history = series["history"]
        forecast = series["forecast"]

        ax = self.canvas.ax
        ax.clear()
        ax.plot(history["business_date"], history["units_sold"], color="#1F6F8B", label="History", linewidth=2)
        ax.plot(forecast["forecast_date"], forecast["forecast_units"], color="#D97706", label="Forecast", linewidth=2)
        ax.fill_between(forecast["forecast_date"], forecast["lower_bound"], forecast["upper_bound"], color="#F4A261", alpha=0.35)
        ax.set_title(f"{sku_code} | {region}", fontsize=11)
        ax.legend(loc="upper left")
        ax.tick_params(axis="x", rotation=20)
        self.canvas.draw()

        if not forecast.empty:
            avg_forecast = forecast["forecast_units"].mean()
            avg_safety = forecast["recommended_safety_stock"].mean()
            avg_reorder = forecast["recommended_reorder_point"].mean()
            self.summary.setText(f"30-day average forecast: {avg_forecast:.1f} units | safety stock: {avg_safety:.1f} | reorder point: {avg_reorder:.1f}")
        self.table_model.set_frame(forecast.head(14))


class ScenarioTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.facility_combo = QComboBox()
        for code, name in get_disruptable_facilities():
            self.facility_combo.addItem(f"{code} | {name}", code)
        self.drop_spin = QDoubleSpinBox()
        self.drop_spin.setRange(5, 100)
        self.drop_spin.setSingleStep(5)
        self.drop_spin.setValue(35)
        run_button = QPushButton("Run Disruption Simulation")
        run_button.clicked.connect(self.refresh)
        controls.addWidget(QLabel("Facility"))
        controls.addWidget(self.facility_combo, 2)
        controls.addWidget(QLabel("Capacity Drop %"))
        controls.addWidget(self.drop_spin)
        controls.addWidget(run_button)
        layout.addLayout(controls)

        self.summary_box = QGroupBox("Simulation Summary")
        form = QFormLayout(self.summary_box)
        self.summary_labels = {key: QLabel("--") for key in ["facility", "fill_rate", "edges", "batches", "message"]}
        form.addRow("Facility", self.summary_labels["facility"])
        form.addRow("Projected Fill Rate", self.summary_labels["fill_rate"])
        form.addRow("Impacted Edges", self.summary_labels["edges"])
        form.addRow("Impacted Batches", self.summary_labels["batches"])
        form.addRow("Message", self.summary_labels["message"])
        layout.addWidget(self.summary_box)

        self.table, self.table_model = create_table()
        layout.addWidget(self.table)

    def refresh(self) -> None:
        result = simulate_disruption(self.facility_combo.currentData(), self.drop_spin.value())
        self.summary_labels["facility"].setText(result["facility_name"])
        self.summary_labels["fill_rate"].setText(f"{result['fill_rate'] * 100:.1f}%")
        self.summary_labels["edges"].setText(str(result["impacted_edges"]))
        self.summary_labels["batches"].setText(str(result["impacted_batches"]))
        self.summary_labels["message"].setText(result["message"])
        self.table_model.set_frame(result["alternative_plan"])


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Oasis Finder - Product Supply-Chain Transparency")
        self.resize(1540, 960)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 18, 20, 18)
        root_layout.setSpacing(14)

        title = QLabel("Oasis Finder")
        title.setObjectName("windowTitle")
        subtitle = QLabel("Product-first supply-chain transparency for fresh-food merchants: click a SKU, then inspect its route, evidence, and stage data.")
        subtitle.setObjectName("windowSubtitle")
        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        tabs = QTabWidget()
        self.product_shelf_tab = ProductShelfTab()
        self.dashboard_tab = DashboardTab()
        self.network_tab = NetworkTab()
        self.trace_tab = TraceabilityTab()
        self.forecast_tab = ForecastTab()
        self.scenario_tab = ScenarioTab()

        tabs.addTab(self.product_shelf_tab, "Product Shelf")
        tabs.addTab(self.dashboard_tab, "Dashboard")
        tabs.addTab(self.network_tab, "Network Mesh")
        tabs.addTab(self.trace_tab, "Traceability")
        tabs.addTab(self.forecast_tab, "Forecasting")
        tabs.addTab(self.scenario_tab, "Scenario Lab")
        root_layout.addWidget(tabs)
        self.setCentralWidget(root)

        self._apply_theme()
        self.refresh_all()

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #F4F7F5;
                color: #1D232A;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 11.5pt;
            }
            QLabel#windowTitle {
                font-size: 24pt;
                font-weight: 700;
                color: #102A43;
            }
            QLabel#windowSubtitle {
                color: #4F5D75;
                font-size: 11pt;
                margin-bottom: 6px;
            }
            QLabel#sectionTitle {
                color: #102A43;
                font-size: 13pt;
                font-weight: 700;
                padding: 4px 0;
            }
            QFrame#heroPanel {
                background: #FFFFFF;
                border: 1px solid #D8E2DC;
                border-radius: 14px;
            }
            QLabel#heroTitle {
                color: #102A43;
                font-size: 24pt;
                font-weight: 800;
            }
            QLabel#heroSubtitle {
                color: #243B53;
                font-size: 12pt;
                font-weight: 600;
            }
            QLabel#heroNote {
                color: #52616B;
                font-size: 10.5pt;
            }
            QTabWidget::pane {
                border: 1px solid #D8E2DC;
                background: #FCFBF8;
                border-radius: 12px;
            }
            QTabBar::tab {
                background: #E7ECEF;
                padding: 10px 16px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 6px;
            }
            QTabBar::tab:selected {
                background: #102A43;
                color: #F7F5EF;
            }
            QFrame#kpiCard, QGroupBox {
                background: #FFFFFF;
                border: 1px solid #DDE7E3;
                border-radius: 14px;
            }
            QLabel#kpiTitle {
                color: #5F6C72;
                font-size: 9.5pt;
            }
            QLabel#kpiValue {
                font-size: 20pt;
                font-weight: 700;
            }
            QLabel#kpiSubtitle {
                color: #7A7F87;
                font-size: 9pt;
            }
            QPushButton {
                background: #102A43;
                color: #F7F5EF;
                border: none;
                border-radius: 10px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #006D77;
            }
            QComboBox, QDoubleSpinBox {
                background: #FFFFFF;
                border: 1px solid #D8E2DC;
                border-radius: 10px;
                padding: 7px 10px;
                min-height: 18px;
            }
            QTableView {
                background: #FFFFFF;
                alternate-background-color: #F3F8F6;
                border: 1px solid #DDE7E3;
                border-radius: 10px;
                gridline-color: #E6ECE8;
                selection-background-color: #D8F3DC;
                selection-color: #102A43;
            }
            QHeaderView::section {
                background: #E7F0EC;
                color: #102A43;
                padding: 8px;
                border: none;
                font-weight: 600;
            }
            """
        )

    def refresh_all(self) -> None:
        self.product_shelf_tab.refresh()
        self.dashboard_tab.refresh()
        self.network_tab.refresh()
        self.trace_tab.refresh()
        self.forecast_tab.refresh()
        self.scenario_tab.refresh()


def run_app() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    app.exec()
