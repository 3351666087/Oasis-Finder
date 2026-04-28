import React, { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "";
const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/updates`;

const I18N = {
  zh: {
    navCustomer: "客户前台",
    navAdmin: "商家后台",
    navApi: "API 文档",
    language: "English",
    heroEyebrow: "鲜食供应链透明展示层",
    heroTitle: "先看商品，再看它背后的供应链。",
    heroBody: "客户先看到商品卡片，再把商品拆成可点击模块，查看时间、地点、批次、温控、质检和图片证据。",
    selectedSku: "当前 SKU",
    liveHint: "商家后台的改动会实时出现在这里。",
    steps: [
      ["先选商品", "像山姆或盒马 App 一样，从名称、类别、价格和证明分进入。"],
      ["再拆元件", "整品路线保留，蛋糕胚、奶油、包装、冷链包等模块可以单独查看。"],
      ["看证据再买", "时间、地点、批次、温控和质检变成可读的购买理由。"],
    ],
    wholeProduct: "整品",
    moduleDissection: "商品模块拆解",
    moduleHint: "点击一个元件，右侧路线会从整品供应链切换到该元件自己的供应链。",
    routeSwitch: "供应链路线",
    wholeRoute: "整品供应链",
    moduleRoute: "元件供应链",
    routeHint: "按标签或阶段筛选路线，点击节点可查看更直观的阶段数据。",
    layerAll: "全部层级",
    nodeDetail: "节点详情",
    nodeHint: "点击任意路线节点查看时间、地点、角色和可展示值。",
    shopperLearns: "客户能看懂什么",
    flowLinks: "条流向链接显示在当前视图",
    proofScore: "证明分",
    price: "价格",
    loading: "正在加载商品路线...",
    variables: {
      batch: "批次",
      production: "生产日期",
      expiry: "到期日期",
      storage: "储存温度",
      quality: "质检分",
      qr: "二维码",
      module: "元件",
      supplierCity: "供应商城市",
      lot: "批号",
      received: "入厂日期",
      inspection: "检验分",
      traceability: "可追溯率",
    },
    admin: {
      eyebrow: "商家后台",
      title: "编辑商品、图片和每层供应链数据",
      intro: "这里给商家使用。改完任意数据后，客户前台会收到实时更新。",
      flowTitle: "商家流程",
      flow: "选择 SKU → 编辑商品 → 编辑流程节点与标签 → 上传图片 → 前台刷新",
      ready: "就绪",
      dataEditor: "商品基础数据",
      dataHint: "第 1 步：编辑商品基础字段。第 2 步：编辑每个层级。第 3 步：上传图片证据。",
      saveProduct: "保存商品基础数据",
      saved: "已保存，客户前台将自动刷新。",
      sections: {
        overview: "整品/批次",
        modules: "商品元件",
        route_nodes: "流程节点/标签",
        route_edges: "流向/边",
        evidence: "证据行",
      },
      selectRecord: "选择要编辑的记录",
      saveLayer: "保存当前层级数据",
      mediaTitle: "商家图片接口",
      saveUrl: "保存 URL",
      upload: "上传图片",
    },
    fields: {
      product_name: "商品名称",
      category: "类别",
      unit_price: "单价",
      shelf_life_days: "保质期天数",
      storage_temp_band: "储存温度带",
      batch_code: "批次编号",
      production_date: "生产日期",
      expiry_date: "到期日期",
      quality_score: "质检分",
      traceability_score: "可追溯率",
      plant_city: "工厂城市",
      qr_code: "二维码",
      module_name: "元件名称",
      module_category: "元件类别",
      supplier_city: "供应商城市",
      lot_code: "批号",
      received_on: "入厂日期",
      inspection_score: "检验分",
      traceability_completeness: "追溯完整度",
      temperature_excursion_minutes: "温度偏离分钟",
      plain_language: "客户可读说明",
      stage: "阶段",
      paint_tag: "标签",
      paint_color: "标签颜色",
      facility_code: "节点编码",
      facility_name: "节点名称",
      facility_type: "节点类型",
      city: "城市",
      role: "角色",
      visible_value: "前台展示值",
      from_code: "起点",
      to_code: "终点",
      flow: "流向内容",
      evidence: "证据编号",
      metric: "指标",
      quality_risk: "质量/风险",
      temperature: "温度",
      location: "地点",
      item: "项目",
      temp: "温度",
      trace: "追溯",
      consumer_message: "客户说明",
      time: "时间",
    },
  },
  en: {
    navCustomer: "Customer view",
    navAdmin: "Merchant studio",
    navApi: "API docs",
    language: "中文",
    heroEyebrow: "Fresh-food transparency layer",
    heroTitle: "Pick a product, then inspect the chain behind it.",
    heroBody: "Shoppers see products first, split them into clickable modules, then inspect time, place, batch, temperature, quality, and image evidence.",
    selectedSku: "Selected SKU",
    liveHint: "Merchant edits appear here in real time.",
    steps: [
      ["Choose product", "Start like a retail app: name, category, price, and proof score."],
      ["Split modules", "Keep the whole-product route while inspecting components such as cake base, cream, packaging, or cold-chain pack."],
      ["Buy with proof", "Time, place, batch, temperature, and quality become readable purchase reasons."],
    ],
    wholeProduct: "Whole product",
    moduleDissection: "Module dissection",
    moduleHint: "Click a component and the route switches from whole-product chain to that component's own supply chain.",
    routeSwitch: "Supply-chain route",
    wholeRoute: "Whole-product supply chain",
    moduleRoute: "Selected module supply chain",
    routeHint: "Filter by tag or stage, then click a node to see clearer stage data.",
    layerAll: "All layers",
    nodeDetail: "Node detail",
    nodeHint: "Click any route node to inspect time, place, role, and display value.",
    shopperLearns: "What the shopper learns",
    flowLinks: "flow links visible in this view",
    proofScore: "proof",
    price: "RMB",
    loading: "Loading product journey...",
    variables: {
      batch: "Batch",
      production: "Production date",
      expiry: "Expiry date",
      storage: "Storage",
      quality: "Quality",
      qr: "QR",
      module: "Module",
      supplierCity: "Supplier city",
      lot: "Lot",
      received: "Received",
      inspection: "Inspection",
      traceability: "Traceability",
    },
    admin: {
      eyebrow: "Merchant backend",
      title: "Edit products, media, and every supply-chain layer",
      intro: "This is for merchants. Any saved change is pushed to the customer frontend.",
      flowTitle: "Merchant flow",
      flow: "Select SKU → edit product → edit flow nodes and tags → upload images → frontend refreshes",
      ready: "Ready",
      dataEditor: "Product data editor",
      dataHint: "Step 1: edit product fields. Step 2: edit every layer. Step 3: upload evidence images.",
      saveProduct: "Save product data",
      saved: "Saved. Customer page will refresh automatically.",
      sections: {
        overview: "Whole product / batch",
        modules: "Product modules",
        route_nodes: "Flow nodes / tags",
        route_edges: "Flows / edges",
        evidence: "Evidence rows",
      },
      selectRecord: "Select record to edit",
      saveLayer: "Save current layer data",
      mediaTitle: "Merchant media interfaces",
      saveUrl: "Save URL",
      upload: "Upload image",
    },
    fields: {
      product_name: "Product name",
      category: "Category",
      unit_price: "Unit price",
      shelf_life_days: "Shelf life days",
      storage_temp_band: "Storage temp band",
      batch_code: "Batch code",
      production_date: "Production date",
      expiry_date: "Expiry date",
      quality_score: "Quality score",
      traceability_score: "Traceability score",
      plant_city: "Plant city",
      qr_code: "QR code",
      module_name: "Module name",
      module_category: "Module category",
      supplier_city: "Supplier city",
      lot_code: "Lot code",
      received_on: "Received on",
      inspection_score: "Inspection score",
      traceability_completeness: "Traceability completeness",
      temperature_excursion_minutes: "Temperature excursion minutes",
      plain_language: "Plain-language message",
      stage: "Stage",
      paint_tag: "Tag",
      paint_color: "Tag color",
      facility_code: "Facility code",
      facility_name: "Facility name",
      facility_type: "Facility type",
      city: "City",
      role: "Role",
      visible_value: "Display value",
      from_code: "From",
      to_code: "To",
      flow: "Flow",
      evidence: "Evidence",
      metric: "Metric",
      quality_risk: "Quality / risk",
      temperature: "Temperature",
      location: "Location",
      item: "Item",
      temp: "Temperature",
      trace: "Trace",
      consumer_message: "Consumer message",
      time: "Time",
    },
  },
};

const CATEGORY_ZH = {
  "Protein / chilled meat": "肉类 / 冷藏鲜食",
  "Dairy / cold chain": "乳制品 / 冷链",
  "Ready meal": "即食餐品",
  "Fresh produce": "新鲜果蔬",
};

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: options.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function mediaUrl(url) {
  if (!url) return "";
  return url.startsWith("http") ? url : `${API}${url}`;
}

function formatDate(value) {
  if (!value) return "--";
  return String(value).slice(0, 10);
}

function fieldLabel(t, key) {
  return t.fields[key] || key.replaceAll("_", " ");
}

function useLanguage() {
  const params = new URLSearchParams(location.search);
  const initial = params.get("lang") || localStorage.getItem("oasis_lang") || "zh";
  const [lang, setLangState] = useState(initial === "en" ? "en" : "zh");
  const setLang = (next) => {
    localStorage.setItem("oasis_lang", next);
    setLangState(next);
  };
  return [lang, setLang, I18N[lang]];
}

function useLiveReload(onEvent) {
  useEffect(() => {
    let closed = false;
    let socket;
    const connect = () => {
      socket = new WebSocket(WS_URL);
      socket.onmessage = (event) => onEvent(JSON.parse(event.data));
      socket.onclose = () => {
        if (!closed) setTimeout(connect, 1100);
      };
    };
    connect();
    return () => {
      closed = true;
      socket?.close();
    };
  }, [onEvent]);
}

function App() {
  const [lang, setLang, t] = useLanguage();
  const isAdmin = location.pathname.startsWith("/admin");
  return isAdmin ? (
    <MerchantStudio lang={lang} setLang={setLang} t={t} />
  ) : (
    <ConsumerExperience lang={lang} setLang={setLang} t={t} />
  );
}

function ConsumerExperience({ lang, setLang, t }) {
  const urlParams = new URLSearchParams(location.search);
  const initialModule = urlParams.get("module");
  const [products, setProducts] = useState([]);
  const [selectedSku, setSelectedSku] = useState(urlParams.get("sku") || "");
  const [detail, setDetail] = useState(null);
  const [selectedModule, setSelectedModule] = useState(initialModule || "whole");
  const [keepInitialModule, setKeepInitialModule] = useState(Boolean(initialModule));
  const [loading, setLoading] = useState(true);

  const loadProducts = async () => {
    const list = await api("/api/products");
    setProducts(list);
    if (!selectedSku && list.length) setSelectedSku(list[0].sku_code);
  };

  const loadDetail = async (sku) => {
    if (!sku) return;
    setLoading(true);
    const payload = await api(`/api/products/${sku}`);
    setDetail(payload);
    setLoading(false);
  };

  useEffect(() => {
    loadProducts();
  }, []);

  useEffect(() => {
    loadDetail(selectedSku);
    if (keepInitialModule) {
      setKeepInitialModule(false);
    } else {
      setSelectedModule("whole");
    }
  }, [selectedSku]);

  useLiveReload((event) => {
    if (event.sku_code === selectedSku) loadDetail(selectedSku);
    loadProducts();
  });

  const selectedProduct = products.find((item) => item.sku_code === selectedSku);
  const selectedModulePayload = detail?.modules?.find((item) => item.module_id === selectedModule);
  const route = selectedModule === "whole"
    ? detail?.route
    : { nodes: selectedModulePayload?.route_nodes || [], edges: selectedModulePayload?.route_edges || [], layout: selectedModulePayload?.route_layout };

  return (
    <div className="app-shell consumer-bg">
      <TopNav mode="consumer" lang={lang} setLang={setLang} t={t} />
      <main className="glass-page">
        <Hero selectedProduct={selectedProduct} lang={lang} t={t} />
        <CustomerGuide t={t} />
        <section className="product-rail">
          {products.map((product) => (
            <button
              className={`product-tile ${product.sku_code === selectedSku ? "active" : ""}`}
              key={product.sku_code}
              onClick={() => setSelectedSku(product.sku_code)}
            >
              <MediaThumb product={product} />
              <span className="tile-category">{lang === "zh" ? CATEGORY_ZH[product.category_label] || product.category_label : product.category_label}</span>
              <strong>{product.product_name}</strong>
              <span>{t.price} {Number(product.unit_price).toFixed(2)} · {t.proofScore} {Number(product.proof_score).toFixed(1)}</span>
            </button>
          ))}
        </section>

        {loading || !detail ? (
          <div className="glass-card loading-card">{t.loading}</div>
        ) : (
          <section className="split-layout">
            <ProductDissection
              detail={detail}
              selectedModule={selectedModule}
              setSelectedModule={setSelectedModule}
              t={t}
            />
            <RouteExplorer route={route} selectedModule={selectedModule} detail={detail} t={t} />
          </section>
        )}
      </main>
    </div>
  );
}

function TopNav({ mode, lang, setLang, t }) {
  const suffix = `?lang=${lang}`;
  return (
    <header className="top-nav">
      <div>
        <span className="brand-mark">OF</span>
        <span className="brand-name">Oasis Finder</span>
      </div>
      <nav>
        <a className={mode === "consumer" ? "active" : ""} href={`/${suffix}`}>{t.navCustomer}</a>
        <a className={mode === "admin" ? "active" : ""} href={`/admin${suffix}`}>{t.navAdmin}</a>
        <a href="/docs">{t.navApi}</a>
        <button className="lang-toggle" onClick={() => setLang(lang === "zh" ? "en" : "zh")}>{t.language}</button>
      </nav>
    </header>
  );
}

function Hero({ selectedProduct, t }) {
  return (
    <section className="hero-grid">
      <div className="hero-copy">
        <span className="eyebrow">{t.heroEyebrow}</span>
        <h1>{t.heroTitle}</h1>
        <p>{t.heroBody}</p>
      </div>
      <div className="hero-metric">
        <span>{t.selectedSku}</span>
        <strong>{selectedProduct?.sku_code || "--"}</strong>
        <p>{selectedProduct?.consumer_claim || t.liveHint}</p>
      </div>
    </section>
  );
}

function CustomerGuide({ t }) {
  return (
    <section className="guide-row" aria-label="How customers use Oasis Finder">
      {t.steps.map((step, index) => (
        <div key={step[0]}>
          <span>{index + 1}</span>
          <strong>{step[0]}</strong>
          <p>{step[1]}</p>
        </div>
      ))}
    </section>
  );
}

function MediaThumb({ product }) {
  const src = mediaUrl(product.primary_media_url);
  return (
    <div className="media-thumb">
      {src ? <img src={src} alt={product.product_name} /> : <span>{product.product_name?.slice(0, 2)}</span>}
    </div>
  );
}

function ProductDissection({ detail, selectedModule, setSelectedModule, t }) {
  const overview = detail.overview;
  return (
    <section className="glass-card dissection-card">
      <div className="section-heading">
        <span className="eyebrow">{t.moduleDissection}</span>
        <h2>{overview.product_name}</h2>
        <p>{t.moduleHint}</p>
      </div>

      <div className="dissection-stage">
        <button
          className={`core-product ${selectedModule === "whole" ? "active" : ""}`}
          onClick={() => setSelectedModule("whole")}
        >
          <span>{t.wholeProduct}</span>
          <strong>{overview.product_name}</strong>
          <small>{overview.batch_code} · {t.variables.traceability} {Number(overview.traceability_score || 0).toFixed(1)}%</small>
        </button>
        <div className="arrow-column">
          <span />
          <span />
          <span />
        </div>
        <div className="module-list">
          {detail.modules.map((module) => (
            <button
              key={module.module_id}
              className={`module-pill ${selectedModule === module.module_id ? "active" : ""}`}
              onClick={() => setSelectedModule(module.module_id)}
            >
              <span>{module.module_category}</span>
              <strong>{moduleDisplayName(module)}</strong>
              <small>{module.supplier_city || "mapped supplier"} · score {Number(module.module_score || 0).toFixed(1)}</small>
            </button>
          ))}
        </div>
      </div>

      <div className="media-strip">
        {detail.media_slots.map((slot) => (
          <div className="media-slot" key={slot.media_key}>
            {slot.url ? <img src={mediaUrl(slot.url)} alt={slot.slot} /> : <IconPlaceholder label={slot.slot} />}
            <div>
              <strong>{slot.slot}</strong>
              <span>{slot.why}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function IconPlaceholder({ label }) {
  return <div className="icon-placeholder">{label.split(" ").map((word) => word[0]).join("").slice(0, 2)}</div>;
}

function nodeKey(node) {
  return String(node?.facility_code || "");
}

function edgeKey(edge) {
  return String(edge?.edge_id || `${edge?.from_code || ""}|${edge?.to_code || ""}|${edge?.stage || ""}|${edge?.evidence || ""}`);
}

function nodeDisplayName(node) {
  return node?.display_name || node?.facility_name || node?.facility_code || "Supply-chain node";
}

function nodeTagLabel(node) {
  return node?.paint_tag || node?.tag_label || node?.material_tag || node?.facility_type || "Node";
}

function nodeAccentColor(node) {
  return node?.paint_color || node?.tag_color || "#67e8f9";
}

function normalizeTag(tag) {
  if (!tag) return null;
  if (typeof tag === "string") return { label: tag, color: "#67e8f9" };
  const label = String(tag.label || tag.name || "").trim();
  if (!label) return null;
  return { label, color: tag.color || "#67e8f9" };
}

function mergeTagPalettes(...groups) {
  const merged = new Map();
  groups.flat().forEach((tag) => {
    const normalized = normalizeTag(tag);
    if (normalized && !merged.has(normalized.label)) merged.set(normalized.label, normalized);
  });
  return Array.from(merged.values());
}

function moduleDisplayName(module) {
  return module?.display_module_name || module?.module_name || module?.module_id || "Product module";
}

function clampCanvasPercent(value) {
  return Math.max(4, Math.min(96, Number(value) || 50));
}

const NODE_CARD_WIDTH = 218;
const NODE_CARD_HEIGHT = 98;
const DIAGRAM_PADDING_X = 150;
const DIAGRAM_PADDING_Y = 92;
const DIAGRAM_COLUMN_GAP = 330;
const DIAGRAM_ROW_GAP = 146;
const DIAGRAM_MIN_WIDTH = 1120;
const DIAGRAM_MIN_HEIGHT = 620;
const STAGE_ORDER = [
  "Raw material origin",
  "Regional aggregation",
  "Ingredient source",
  "Quality / compliance gate",
  "Processing / packing",
  "Distribution center",
  "Logistics node",
  "Retail shelf",
];
const DEFAULT_TAGS = [
  { label: "Raw material", color: "#67e8f9" },
  { label: "Quality gate", color: "#86efac" },
  { label: "Processing", color: "#fbbf24" },
  { label: "Logistics", color: "#f472b6" },
  { label: "Retail", color: "#a78bfa" },
];

function stageRank(stage) {
  const index = STAGE_ORDER.indexOf(stage || "");
  return index === -1 ? STAGE_ORDER.length : index;
}

function numberOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clampNumber(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function groupNodesByStage(nodes) {
  const groups = new Map();
  nodes.forEach((node) => {
    const stage = node.stage || "Editable stage";
    if (!groups.has(stage)) groups.set(stage, []);
    groups.get(stage).push(node);
  });
  return Array.from(groups.entries())
    .map(([stage, stageNodes]) => ({
      stage,
      nodes: [...stageNodes].sort((a, b) => (
        nodeTagLabel(a).localeCompare(nodeTagLabel(b))
        || nodeDisplayName(a).localeCompare(nodeDisplayName(b))
      )),
    }))
    .sort((a, b) => stageRank(a.stage) - stageRank(b.stage) || a.stage.localeCompare(b.stage));
}

function buildDiagramLayout(rawNodes, { preferSaved = true, routeLayout = null } = {}) {
  const groups = groupNodesByStage(rawNodes || []);
  const layoutNodeWidth = Number(routeLayout?.node_width) || NODE_CARD_WIDTH;
  const layoutNodeHeight = Number(routeLayout?.node_height) || NODE_CARD_HEIGHT;
  const maxRows = Math.max(1, ...groups.map((group) => group.nodes.length));
  const savedMaxX = Math.max(0, ...(rawNodes || []).map((node) => numberOrNull(node.mesh_px_x) || 0));
  const savedMaxY = Math.max(0, ...(rawNodes || []).map((node) => numberOrNull(node.mesh_px_y) || 0));
  let width = Math.max(
    Number(routeLayout?.width) || 0,
    DIAGRAM_MIN_WIDTH,
    DIAGRAM_PADDING_X * 2 + layoutNodeWidth + Math.max(0, groups.length - 1) * DIAGRAM_COLUMN_GAP,
    savedMaxX + layoutNodeWidth + DIAGRAM_PADDING_X,
  );
  let height = Math.max(
    Number(routeLayout?.height) || 0,
    DIAGRAM_MIN_HEIGHT,
    DIAGRAM_PADDING_Y * 2 + layoutNodeHeight + Math.max(0, maxRows - 1) * DIAGRAM_ROW_GAP,
    savedMaxY + layoutNodeHeight + DIAGRAM_PADDING_Y,
  );
  const positioned = [];
  const bands = [];
  const occupied = [];

  const hasOverlap = (x, y) => {
    const left = x - layoutNodeWidth / 2;
    const right = x + layoutNodeWidth / 2;
    const top = y - layoutNodeHeight / 2;
    const bottom = y + layoutNodeHeight / 2;
    return occupied.some((box) => left < box.right && right > box.left && top < box.bottom && bottom > box.top);
  };

  groups.forEach((group, groupIndex) => {
    const savedBand = routeLayout?.bands?.find((band) => band.stage === group.stage);
    const x = savedBand
      ? Number(savedBand.x) + (Number(savedBand.width) / 2)
      : DIAGRAM_PADDING_X + groupIndex * DIAGRAM_COLUMN_GAP;
    bands.push({
      stage: group.stage,
      x: savedBand ? Number(savedBand.x) : x - layoutNodeWidth / 2 - 28,
      y: savedBand ? Number(savedBand.y || 34) : 34,
      width: savedBand ? Number(savedBand.width) : layoutNodeWidth + 56,
      height: savedBand ? Math.max(Number(savedBand.height || 0), height - 68) : height - 68,
    });
    group.nodes.forEach((node, rowIndex) => {
      const savedX = preferSaved ? numberOrNull(node.mesh_px_x) : null;
      const savedY = preferSaved ? numberOrNull(node.mesh_px_y) : null;
      const percentX = preferSaved && numberOrNull(node.mesh_x) != null ? (numberOrNull(node.mesh_x) / 100) * width : null;
      const percentY = preferSaved && numberOrNull(node.mesh_y) != null ? (numberOrNull(node.mesh_y) / 100) * height : null;
      let nodeX = savedX ?? (node.layout_locked ? percentX : null) ?? x;
      let nodeY = savedY ?? (node.layout_locked ? percentY : null) ?? (DIAGRAM_PADDING_Y + rowIndex * DIAGRAM_ROW_GAP + ((groupIndex % 2) * 12));
      nodeX = clampNumber(nodeX, layoutNodeWidth / 2 + 18, width - layoutNodeWidth / 2 - 18);
      nodeY = clampNumber(nodeY, layoutNodeHeight / 2 + 18, height - layoutNodeHeight / 2 - 18);
      while (hasOverlap(nodeX, nodeY)) {
        nodeY += DIAGRAM_ROW_GAP;
        if (nodeY + layoutNodeHeight / 2 + DIAGRAM_PADDING_Y > height) {
          height += DIAGRAM_ROW_GAP;
        }
      }
      occupied.push({
        left: nodeX - layoutNodeWidth / 2,
        top: nodeY - layoutNodeHeight / 2,
        right: nodeX + layoutNodeWidth / 2,
        bottom: nodeY + layoutNodeHeight / 2,
      });
      positioned.push({
        ...node,
        mesh_px_x: nodeX,
        mesh_px_y: nodeY,
      });
    });
  });

  return {
    width,
    height,
    nodes: positioned,
    bands: bands.map((band) => ({ ...band, height: Math.max(band.height, height - 68) })),
    nodeMap: new Map(positioned.map((node) => [nodeKey(node), node])),
    nodeWidth: layoutNodeWidth,
    nodeHeight: layoutNodeHeight,
  };
}

function diagramEdgePath(from, to, layout, index = 0) {
  const dx = Number(to.mesh_px_x) - Number(from.mesh_px_x);
  const dy = Number(to.mesh_px_y) - Number(from.mesh_px_y);
  const preferHorizontal = Math.abs(dx) >= Math.abs(dy) && Math.abs(dx) > layout.nodeWidth * 0.45;
  const fromSide = preferHorizontal ? (dx >= 0 ? "right" : "left") : (dy >= 0 ? "bottom" : "top");
  const toSide = preferHorizontal ? (dx >= 0 ? "left" : "right") : (dy >= 0 ? "top" : "bottom");
  const start = connectionAnchor(from, layout, fromSide);
  const end = connectionAnchor(to, layout, toSide);
  const offset = ((index % 5) - 2) * 14;
  if (fromSide === "right" || fromSide === "left") {
    const direction = fromSide === "right" ? 1 : -1;
    const startOut = start.x + direction * 42;
    const endIn = end.x - direction * 42;
    const middleX = startOut + ((endIn - startOut) / 2) + offset;
    return `M ${start.x} ${start.y} L ${startOut} ${start.y} L ${middleX} ${start.y} L ${middleX} ${end.y} L ${endIn} ${end.y} L ${end.x} ${end.y}`;
  }
  const direction = fromSide === "bottom" ? 1 : -1;
  const startOut = start.y + direction * 42;
  const endIn = end.y - direction * 42;
  const middleY = startOut + ((endIn - startOut) / 2) + offset;
  return `M ${start.x} ${start.y} L ${start.x} ${startOut} L ${start.x} ${middleY} L ${end.x} ${middleY} L ${end.x} ${endIn} L ${end.x} ${end.y}`;
}

function diagramPointPath(start, end) {
  const middleX = start.x + ((end.x - start.x) / 2);
  return `M ${start.x} ${start.y} L ${middleX} ${start.y} L ${middleX} ${end.y} L ${end.x} ${end.y}`;
}

function connectionAnchor(node, layout, side) {
  const x = Number(node.mesh_px_x);
  const y = Number(node.mesh_px_y);
  if (side === "left") return { x: x - layout.nodeWidth / 2, y };
  if (side === "top") return { x, y: y - layout.nodeHeight / 2 };
  if (side === "bottom") return { x, y: y + layout.nodeHeight / 2 };
  return { x: x + layout.nodeWidth / 2, y };
}

function isTypingTarget(target) {
  const tag = target?.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target?.isContentEditable;
}

function requestBrowserFullscreen() {
  if (document.fullscreenElement) return;
  document.documentElement.requestFullscreen?.().catch(() => {});
}

function DiagramCanvas({
  route,
  nodes,
  edges,
  activeNodeCode,
  onNodeSelect,
  selectedEdgeId = "",
  onEdgeSelect,
  editable = false,
  nodesInteractive = true,
  connectFrom = "",
  onConnectNodes,
  onNodeDrag,
  onNodeDragEnd,
  onTagDrop,
  className = "",
  preferSaved = true,
  fitPadding = 44,
}) {
  const viewportRef = useRef(null);
  const markerId = useRef(`diagramArrow-${Math.random().toString(36).slice(2)}`);
  const [view, setView] = useState({ scale: 1, x: 0, y: 0 });
  const [panning, setPanning] = useState(null);
  const [draggingNode, setDraggingNode] = useState(null);
  const [connectionDraft, setConnectionDraft] = useState(null);
  const [connectionTargetCode, setConnectionTargetCode] = useState("");
  const layout = useMemo(
    () => buildDiagramLayout(nodes, { preferSaved, routeLayout: route?.layout }),
    [nodes, preferSaved, route?.layout],
  );
  const visibleCodes = useMemo(() => new Set(layout.nodes.map(nodeKey)), [layout.nodes]);
  const visibleEdges = useMemo(
    () => (edges || []).filter((edge) => visibleCodes.has(String(edge.from_code)) && visibleCodes.has(String(edge.to_code))),
    [edges, visibleCodes],
  );

  const fitToViewport = () => {
    const rect = viewportRef.current?.getBoundingClientRect();
    if (!rect?.width || !rect?.height) return;
    const nextScale = clampNumber(
      Math.min((rect.width - fitPadding) / layout.width, (rect.height - fitPadding) / layout.height, 1),
      0.18,
      1,
    );
    setView({
      scale: nextScale,
      x: (rect.width - layout.width * nextScale) / 2,
      y: (rect.height - layout.height * nextScale) / 2,
    });
  };

  useEffect(() => {
    fitToViewport();
    const viewport = viewportRef.current;
    if (!viewport || typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver(fitToViewport);
    observer.observe(viewport);
    return () => observer.disconnect();
  }, [layout.width, layout.height, fitPadding]);

  const clientToDiagram = (event, currentView = view) => {
    const rect = viewportRef.current?.getBoundingClientRect();
    if (!rect) return { x: layout.width / 2, y: layout.height / 2 };
    return {
      x: clampNumber((event.clientX - rect.left - currentView.x) / currentView.scale, layout.nodeWidth / 2 + 18, layout.width - layout.nodeWidth / 2 - 18),
      y: clampNumber((event.clientY - rect.top - currentView.y) / currentView.scale, layout.nodeHeight / 2 + 18, layout.height - layout.nodeHeight / 2 - 18),
    };
  };

  const nodeAtPoint = (point, excludeCode = "") => layout.nodes.find((node) => {
    const code = nodeKey(node);
    if (code === excludeCode) return false;
    return (
      point.x >= node.mesh_px_x - layout.nodeWidth / 2
      && point.x <= node.mesh_px_x + layout.nodeWidth / 2
      && point.y >= node.mesh_px_y - layout.nodeHeight / 2
      && point.y <= node.mesh_px_y + layout.nodeHeight / 2
    );
  });

  const nodeFromPointerEvent = (event, excludeCode = "") => {
    const element = document.elementFromPoint(event.clientX, event.clientY)?.closest?.(".diagram-node");
    const code = element?.dataset?.nodeCode;
    if (code && code !== excludeCode) {
      return layout.nodeMap.get(code) || null;
    }
    return nodeAtPoint(clientToDiagram(event), excludeCode) || null;
  };

  const zoomAround = (clientX, clientY, factor) => {
    const rect = viewportRef.current?.getBoundingClientRect();
    if (!rect) return;
    setView((current) => {
      const nextScale = clampNumber(current.scale * factor, 0.2, 2.4);
      const pointerX = clientX - rect.left;
      const pointerY = clientY - rect.top;
      const diagramX = (pointerX - current.x) / current.scale;
      const diagramY = (pointerY - current.y) / current.scale;
      return {
        scale: nextScale,
        x: pointerX - diagramX * nextScale,
        y: pointerY - diagramY * nextScale,
      };
    });
  };

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return undefined;
    const handleWheel = (event) => {
      if (isTypingTarget(event.target)) return;
      event.preventDefault();
      event.stopPropagation();
      zoomAround(event.clientX, event.clientY, event.deltaY < 0 ? 1.12 : 0.88);
    };
    viewport.addEventListener("wheel", handleWheel, { passive: false });
    return () => viewport.removeEventListener("wheel", handleWheel);
  });

  const handleViewportPointerDown = (event) => {
    if (event.button !== 0 || event.target.closest?.(".diagram-node") || event.target.closest?.(".diagram-edge")) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    setPanning({
      pointerId: event.pointerId,
      clientX: event.clientX,
      clientY: event.clientY,
      viewX: view.x,
      viewY: view.y,
    });
  };

  const handlePointerMove = (event) => {
    if (connectionDraft) {
      const point = clientToDiagram(event);
      const target = nodeFromPointerEvent(event, connectionDraft.fromCode);
      setConnectionTargetCode(target ? nodeKey(target) : "");
      setConnectionDraft({ ...connectionDraft, point });
      return;
    }
    if (draggingNode) {
      const moved = draggingNode.moved || Math.abs(event.clientX - draggingNode.clientX) > 3 || Math.abs(event.clientY - draggingNode.clientY) > 3;
      const point = clientToDiagram(event);
      setDraggingNode({ ...draggingNode, moved, point });
      onNodeDrag?.(draggingNode.code, point);
      return;
    }
    if (panning) {
      setView((current) => ({
        ...current,
        x: panning.viewX + event.clientX - panning.clientX,
        y: panning.viewY + event.clientY - panning.clientY,
      }));
    }
  };

  const handlePointerUp = async (event) => {
    viewportRef.current?.releasePointerCapture?.(event.pointerId);
    if (connectionDraft) {
      const point = connectionDraft.point || clientToDiagram(event);
      const target = nodeFromPointerEvent(event, connectionDraft.fromCode);
      const fromCode = connectionDraft.fromCode;
      setConnectionDraft(null);
      setConnectionTargetCode("");
      if (target) {
        await onConnectNodes?.(fromCode, nodeKey(target));
      }
      return;
    }
    if (draggingNode) {
      const node = layout.nodeMap.get(draggingNode.code);
      const point = draggingNode.point || clientToDiagram(event);
      const moved = draggingNode.moved || Math.abs(event.clientX - draggingNode.clientX) > 3 || Math.abs(event.clientY - draggingNode.clientY) > 3;
      setDraggingNode(null);
      if (moved) {
        await onNodeDragEnd?.(draggingNode.code, point);
      } else if (node) {
        onNodeSelect?.(node);
      }
      return;
    }
    if (panning) setPanning(null);
  };

  const handleNodePointerDown = (event, node) => {
    if (!nodesInteractive) return;
    event.stopPropagation();
    if (!editable || connectFrom) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    setDraggingNode({
      code: nodeKey(node),
      clientX: event.clientX,
      clientY: event.clientY,
      moved: false,
      point: { x: node.mesh_px_x, y: node.mesh_px_y },
    });
    onNodeSelect?.(node);
  };

  const startConnection = (event, node, side) => {
    if (!editable || !onConnectNodes) return;
    event.preventDefault();
    event.stopPropagation();
    viewportRef.current?.setPointerCapture?.(event.pointerId);
    const start = connectionAnchor(node, layout, side);
    setConnectionDraft({
      fromCode: nodeKey(node),
      side,
      start,
      point: start,
    });
    setConnectionTargetCode("");
    onNodeSelect?.(node);
  };

  const zoomButton = (factor) => {
    const rect = viewportRef.current?.getBoundingClientRect();
    if (!rect) return;
    zoomAround(rect.left + rect.width / 2, rect.top + rect.height / 2, factor);
  };

  return (
    <div
      className={`diagram-viewport ${className}`}
      ref={viewportRef}
      onPointerDown={handleViewportPointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <div
        className="diagram-controls"
        onPointerDown={(event) => event.stopPropagation()}
        onClick={(event) => event.stopPropagation()}
      >
        <button type="button" onClick={() => zoomButton(0.86)} aria-label="Zoom out">-</button>
        <span>{Math.round(view.scale * 100)}%</span>
        <button type="button" onClick={() => zoomButton(1.16)} aria-label="Zoom in">+</button>
        <button type="button" onClick={fitToViewport}>Fit</button>
      </div>
      <div
        className="diagram-stage"
        style={{
          width: `${layout.width}px`,
          height: `${layout.height}px`,
          transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})`,
        }}
      >
        <svg className="diagram-svg" viewBox={`0 0 ${layout.width} ${layout.height}`} aria-hidden="true">
          <defs>
            <pattern id={`${markerId.current}-grid`} width="24" height="24" patternUnits="userSpaceOnUse">
              <path d="M 24 0 L 0 0 0 24" />
            </pattern>
            <marker id={markerId.current} viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M 0 0 L 10 5 L 0 10 z" />
            </marker>
          </defs>
          <rect className="diagram-grid-fill" x="0" y="0" width={layout.width} height={layout.height} fill={`url(#${markerId.current}-grid)`} />
          {layout.bands.map((band) => (
            <g className="diagram-band" key={band.stage}>
              <rect x={band.x} y={band.y} width={band.width} height={band.height} rx="10" />
              <text x={band.x + 16} y={band.y + 24}>{band.stage}</text>
            </g>
          ))}
          {visibleEdges.map((edge, index) => {
            const from = layout.nodeMap.get(String(edge.from_code));
            const to = layout.nodeMap.get(String(edge.to_code));
            if (!from || !to) return null;
            const edgeId = edgeKey(edge);
            return (
              <path
                className={`diagram-edge ${selectedEdgeId === edgeId ? "selected" : ""} ${onEdgeSelect ? "selectable" : ""}`}
                key={edgeId}
                d={diagramEdgePath(from, to, layout, index)}
                markerEnd={`url(#${markerId.current})`}
                onPointerDown={(event) => {
                  if (!onEdgeSelect) return;
                  event.stopPropagation();
                  onEdgeSelect(edge);
                }}
              />
            );
          })}
          {connectionDraft && (
            <path
              className={`diagram-connection-preview ${connectionTargetCode ? "valid" : ""}`}
              d={diagramPointPath(connectionDraft.start, connectionDraft.point)}
              markerEnd={`url(#${markerId.current})`}
            />
          )}
        </svg>
        {layout.nodes.map((node) => {
          const NodeTag = nodesInteractive ? "button" : "div";
          const code = nodeKey(node);
          return (
            <NodeTag
              key={code}
              type={nodesInteractive ? "button" : undefined}
              className={`mesh-node diagram-node ${editable ? "admin" : ""} ${activeNodeCode === code ? "active" : ""} ${connectFrom === code ? "source" : ""}`}
              data-node-code={code}
              style={{
                left: `${node.mesh_px_x}px`,
                top: `${node.mesh_px_y}px`,
                width: `${layout.nodeWidth}px`,
                minHeight: `${layout.nodeHeight}px`,
                "--node-accent": nodeAccentColor(node),
                "--node-accent-soft": `${nodeAccentColor(node)}24`,
                "--node-overlay-opacity": node.paint_tag || node.tag_label || node.material_tag ? 0.42 : 0.12,
              }}
              onPointerDown={(event) => handleNodePointerDown(event, node)}
              onDragOver={(event) => {
                if (!editable || !onTagDrop) return;
                event.preventDefault();
              }}
              onDrop={(event) => {
                if (!editable || !onTagDrop) return;
                event.preventDefault();
                event.stopPropagation();
                const text = event.dataTransfer.getData("application/json") || event.dataTransfer.getData("text/plain");
                if (!text) return;
                try {
                  onTagDrop(node, JSON.parse(text));
                } catch {
                  onTagDrop(node, { label: text, color: "#67e8f9" });
                }
              }}
              onClick={(event) => {
                if (!nodesInteractive) return;
                event.stopPropagation();
                if (nodesInteractive && (!editable || connectFrom)) onNodeSelect?.(node);
              }}
            >
              <span>{nodeTagLabel(node)} · {node.stage || "stage"}</span>
              <strong>{nodeDisplayName(node)}</strong>
              <small>{node.city || node.role || node.facility_type || "--"}</small>
              {editable && onConnectNodes && ["left", "right", "top", "bottom"].map((side) => (
                <i
                  key={side}
                  className={`connector-handle ${side} ${connectionTargetCode === code ? "snap-active" : ""}`}
                  title={`Drag ${side} connector`}
                  onPointerDown={(event) => startConnection(event, node, side)}
                  onClick={(event) => event.stopPropagation()}
                />
              ))}
            </NodeTag>
          );
        })}
      </div>
    </div>
  );
}

function FullScreenModal({ title, subtitle, onClose, children }) {
  const shellRef = useRef(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const shell = shellRef.current;
    let nativeFullscreenActive = Boolean(document.fullscreenElement);
    const handleKeyDown = (event) => {
      if (event.key !== "Escape" || isTypingTarget(event.target)) return;
      if (document.fullscreenElement) return;
      onCloseRef.current();
    };
    const handleFullscreenChange = () => {
      if (nativeFullscreenActive && !document.fullscreenElement) onCloseRef.current();
    };
    document.body.classList.add("modal-open");
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    if (shell?.requestFullscreen && !document.fullscreenElement) {
      shell.requestFullscreen()
        .then(() => {
          nativeFullscreenActive = true;
        })
        .catch(() => {
          nativeFullscreenActive = false;
        });
    }
    return () => {
      document.body.classList.remove("modal-open");
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, []);

  return createPortal((
    <div className="fullscreen-shell" ref={shellRef} role="dialog" aria-modal="true" aria-label={title}>
      <header className="fullscreen-header">
        <div>
          <span className="eyebrow">{subtitle}</span>
          <h2>{title}</h2>
        </div>
        <button type="button" className="close-action" onClick={onClose} aria-label="Close">Close</button>
      </header>
      {children}
    </div>
  ), document.body);
}

function RouteExplorer({ route, selectedModule, detail, t }) {
  return <RouteMeshExplorer route={route} selectedModule={selectedModule} detail={detail} t={t} />;
}

function RouteMeshExplorer({ route, selectedModule, detail, t }) {
  const nodes = useMemo(() => route?.nodes || [], [route]);
  const edges = useMemo(() => route?.edges || [], [route]);
  const selectedModulePayload = detail.modules.find((module) => module.module_id === selectedModule);
  const layerOptions = useMemo(() => {
    const tags = Array.from(new Set(nodes.map((node) => nodeTagLabel(node)).filter(Boolean)));
    const stages = Array.from(new Set(nodes.map((node) => node.stage).filter(Boolean)));
    return [
      { key: "ALL", label: t.layerAll },
      ...tags.map((tag) => ({ key: `tag:${tag}`, label: tag })),
      ...stages.map((stage) => ({ key: `stage:${stage}`, label: stage })),
    ];
  }, [nodes, t.layerAll]);
  const [layer, setLayer] = useState("ALL");
  const [activeNodeCode, setActiveNodeCode] = useState("");
  const [showcaseOpen, setShowcaseOpen] = useState(false);

  useEffect(() => {
    setLayer("ALL");
    setActiveNodeCode("");
  }, [selectedModule]);

  const visibleNodes = useMemo(() => {
    if (layer === "ALL") return nodes;
    if (layer.startsWith("tag:")) {
      const tag = layer.slice(4);
      return nodes.filter((node) => nodeTagLabel(node) === tag);
    }
    if (layer.startsWith("stage:")) {
      const stage = layer.slice(6);
      return nodes.filter((node) => node.stage === stage);
    }
    return nodes;
  }, [nodes, layer]);
  const visibleCodes = useMemo(() => new Set(visibleNodes.map(nodeKey)), [visibleNodes]);
  const visibleEdges = useMemo(
    () => edges.filter((edge) => visibleCodes.has(String(edge.from_code)) && visibleCodes.has(String(edge.to_code))),
    [edges, visibleCodes],
  );
  const activeNode = visibleNodes.find((node) => nodeKey(node) === activeNodeCode) || visibleNodes[0];
  const activeCode = activeNode ? nodeKey(activeNode) : "";
  const openShowcase = () => {
    requestBrowserFullscreen();
    setShowcaseOpen(true);
  };

  const evidence = selectedModule === "whole"
    ? detail.evidence.slice(0, 5)
    : selectedModulePayload?.plain_language;
  const variableSet = selectedModule === "whole"
    ? [
        [t.variables.batch, detail.overview.batch_code],
        [t.variables.production, formatDate(detail.overview.production_date)],
        [t.variables.expiry, formatDate(detail.overview.expiry_date)],
        [t.variables.storage, detail.overview.storage_temp_band],
        [t.variables.quality, Number(detail.overview.quality_score || 0).toFixed(1)],
        [t.variables.qr, detail.overview.qr_code],
      ]
    : [
        [t.variables.module, moduleDisplayName(selectedModulePayload)],
        [t.variables.supplierCity, selectedModulePayload?.supplier_city],
        [t.variables.lot, selectedModulePayload?.lot_code],
        [t.variables.received, formatDate(selectedModulePayload?.received_on)],
        [t.variables.inspection, Number(selectedModulePayload?.inspection_score || 0).toFixed(1)],
        [t.variables.traceability, `${(Number(selectedModulePayload?.traceability_completeness || 0) * 100).toFixed(1)}%`],
      ];

  return (
    <section className="glass-card route-card">
      <div className="section-heading">
        <span className="eyebrow">{t.routeSwitch}</span>
        <h2>{selectedModule === "whole" ? t.wholeRoute : t.moduleRoute}</h2>
        <p>{t.routeHint}</p>
      </div>
      <div className="layer-filter">
        {layerOptions.map((option) => (
          <button key={option.key} className={layer === option.key ? "active" : ""} onClick={() => setLayer(option.key)}>
            {option.label}
          </button>
        ))}
      </div>

      <div
        className="route-thumbnail"
        role="button"
        tabIndex={0}
        onClick={openShowcase}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openShowcase();
          }
        }}
      >
        <DiagramCanvas
          route={route}
          nodes={visibleNodes}
          edges={visibleEdges}
          activeNodeCode={activeCode}
          nodesInteractive={false}
          className="diagram-thumbnail"
          fitPadding={20}
        />
        <span className="thumbnail-action">Open full screen</span>
      </div>

      <NodeDetail node={activeNode} t={t} />
      <EvidenceMatrix variables={variableSet} />
      <div className="proof-panel">
        <h3>{t.shopperLearns}</h3>
        {typeof evidence === "string" ? (
          <p>{evidence}</p>
        ) : Array.isArray(evidence) && evidence.length ? (
          evidence.map((row) => (
            <p key={row.evidence_id || `${row.stage}-${row.evidence}`}>
              <strong>{row.stage}</strong> · {formatDate(row.time)} · {row.metric}
            </p>
          ))
        ) : (
          <p>{t.nodeHint}</p>
        )}
        <span className="edge-count">{visibleEdges.length} {t.flowLinks}</span>
      </div>
      {showcaseOpen && (
        <RouteShowcase
          route={route}
          nodes={visibleNodes}
          edges={visibleEdges}
          activeNode={activeNode}
          activeNodeCode={activeCode}
          setActiveNodeCode={setActiveNodeCode}
          title={selectedModule === "whole" ? t.wholeRoute : t.moduleRoute}
          evidence={evidence}
          variableSet={variableSet}
          t={t}
          onClose={() => setShowcaseOpen(false)}
        />
      )}
    </section>
  );
}

function RouteShowcase({ route, nodes, edges, activeNode, activeNodeCode, setActiveNodeCode, title, evidence, variableSet, t, onClose }) {
  return (
    <FullScreenModal title={title} subtitle={t.routeSwitch} onClose={onClose}>
      <div className="fullscreen-content showcase-content">
        <DiagramCanvas
          route={route}
          nodes={nodes}
          edges={edges}
          activeNodeCode={activeNodeCode}
          onNodeSelect={(node) => setActiveNodeCode(nodeKey(node))}
          className="diagram-fullscreen"
          fitPadding={68}
        />
        <aside className="fullscreen-inspector">
          <NodeDetail node={activeNode} t={t} />
          <EvidenceMatrix variables={variableSet} />
          <div className="proof-panel">
            <h3>{t.shopperLearns}</h3>
            {typeof evidence === "string" ? (
              <p>{evidence}</p>
            ) : Array.isArray(evidence) && evidence.length ? (
              evidence.map((row) => (
                <p key={row.evidence_id || `${row.stage}-${row.evidence}`}>
                  <strong>{row.stage}</strong> · {formatDate(row.time)} · {row.metric}
                </p>
              ))
            ) : (
              <p>{t.nodeHint}</p>
            )}
            <span className="edge-count">{edges.length} {t.flowLinks}</span>
          </div>
        </aside>
      </div>
    </FullScreenModal>
  );
}

function NodeDetail({ node, t }) {
  if (!node) return null;
  return (
    <div className="node-detail-panel">
      <div>
        <span>{t.nodeDetail}</span>
        <strong>{nodeDisplayName(node)}</strong>
      </div>
      <p>{node.visible_value || t.nodeHint}</p>
      <div className="node-detail-grid">
        <small>{fieldLabel(t, "city")}: {node.city || "--"}</small>
        <small>{fieldLabel(t, "paint_tag")}: {nodeTagLabel(node)}</small>
        <small>{fieldLabel(t, "facility_type")}: {node.facility_type || "--"}</small>
        <small>{fieldLabel(t, "role")}: {node.role || "--"}</small>
      </div>
    </div>
  );
}

function EvidenceMatrix({ variables }) {
  return (
    <div className="variable-grid">
      {variables.map(([label, value]) => (
        <div className="variable-chip" key={label}>
          <span>{label}</span>
          <strong>{value || "--"}</strong>
        </div>
      ))}
    </div>
  );
}

function MerchantStudio({ lang, setLang, t }) {
  const [products, setProducts] = useState([]);
  const [selectedSku, setSelectedSku] = useState("");
  const [detail, setDetail] = useState(null);
  const [form, setForm] = useState({});
  const [status, setStatus] = useState(t.admin.ready);

  const loadProducts = async () => {
    const list = await api("/api/products");
    setProducts(list);
    if (!selectedSku && list.length) setSelectedSku(list[0].sku_code);
  };
  const loadDetail = async (sku) => {
    if (!sku) return;
    const payload = await api(`/api/products/${sku}`);
    setDetail(payload);
    setForm({
      product_name: payload.overview.product_name,
      category: payload.overview.category,
      unit_price: payload.overview.unit_price,
      shelf_life_days: payload.overview.shelf_life_days,
      storage_temp_band: payload.overview.storage_temp_band,
    });
  };

  useEffect(() => {
    loadProducts();
  }, []);
  useEffect(() => {
    loadDetail(selectedSku);
  }, [selectedSku]);
  useLiveReload((event) => {
    setStatus(`Live update: ${event.type}`);
    loadProducts();
    if (event.sku_code === selectedSku) loadDetail(selectedSku);
  });

  const saveProduct = async () => {
    setStatus("Saving...");
    await api(`/api/admin/products/${selectedSku}`, { method: "PATCH", body: JSON.stringify(form) });
    setStatus(t.admin.saved);
  };

  return (
    <div className="app-shell admin-bg">
      <TopNav mode="admin" lang={lang} setLang={setLang} t={t} />
      <main className="admin-layout">
        <aside className="glass-card admin-sidebar">
          <span className="eyebrow">{t.admin.eyebrow}</span>
          <h1>{t.admin.title}</h1>
          <p>{t.admin.intro}</p>
          <div className="admin-workflow">
            <span>{t.admin.flowTitle}</span>
            <p>{t.admin.flow}</p>
          </div>
          <div className="status-pill">{status}</div>
          {products.map((product) => (
            <button
              className={`admin-product ${product.sku_code === selectedSku ? "active" : ""}`}
              key={product.sku_code}
              onClick={() => setSelectedSku(product.sku_code)}
            >
              <strong>{product.product_name}</strong>
              <span>{product.sku_code}</span>
            </button>
          ))}
        </aside>

        {detail && (
          <section className="admin-main-stack">
            <section className="glass-card editor-panel">
              <div className="section-heading">
                <span className="eyebrow">{t.admin.dataEditor}</span>
                <h2>{detail.overview.product_name}</h2>
                <p>{t.admin.dataHint}</p>
              </div>
              <div className="form-grid">
                <Input label={fieldLabel(t, "product_name")} value={form.product_name} onChange={(v) => setForm({ ...form, product_name: v })} />
                <Input label={fieldLabel(t, "category")} value={form.category} onChange={(v) => setForm({ ...form, category: v })} />
                <Input label={fieldLabel(t, "unit_price")} type="number" value={form.unit_price} onChange={(v) => setForm({ ...form, unit_price: Number(v) })} />
                <Input label={fieldLabel(t, "shelf_life_days")} type="number" value={form.shelf_life_days} onChange={(v) => setForm({ ...form, shelf_life_days: Number(v) })} />
                <Input label={fieldLabel(t, "storage_temp_band")} value={form.storage_temp_band} onChange={(v) => setForm({ ...form, storage_temp_band: v })} />
              </div>
              <button className="primary-action" onClick={saveProduct}>{t.admin.saveProduct}</button>
            </section>

            <LayerEditor
              sku={selectedSku}
              detail={detail}
              t={t}
              onSaved={() => loadDetail(selectedSku)}
              setStatus={setStatus}
            />

            <section className="glass-card editor-panel">
              <div className="section-heading">
                <span className="eyebrow">{t.admin.mediaTitle}</span>
                <h2>{t.admin.mediaTitle}</h2>
              </div>
              <div className="media-editor-grid">
                {detail.media_slots.map((slot) => (
                  <MediaEditor
                    key={slot.media_key}
                    sku={selectedSku}
                    slot={slot}
                    onSaved={() => loadDetail(selectedSku)}
                    setStatus={setStatus}
                    t={t}
                  />
                ))}
              </div>
            </section>
          </section>
        )}
      </main>
    </div>
  );
}

function defaultDetailRecord(sectionKey, detail) {
  const now = Date.now();
  const nodes = detail?.route?.nodes || [];
  if (sectionKey === "modules") {
    return {
      module_id: `custom-module-${now}`,
      module_name: "New product component",
      module_category: "Editable component",
      supplier_city: "Editable city",
      lot_code: `LOT-${now}`,
      received_on: new Date().toISOString().slice(0, 10),
      inspection_score: 90,
      traceability_completeness: 0.9,
      temperature_excursion_minutes: 0,
      plain_language: "This component has editable supplier, lot, inspection, and traceability data.",
    };
  }
  if (sectionKey === "route_nodes") {
    return {
      facility_code: `custom-node-${now}`,
      display_name: "New supply-chain checkpoint",
      facility_name: "New supply-chain checkpoint",
      stage: "Ingredient source",
      paint_tag: "Raw material",
      paint_color: "#67e8f9",
      facility_type: "editable_checkpoint",
      city: "Editable city",
      role: "Editable role",
      visible_value: "Add time, location, lot, temperature, quality, and certificate data here.",
      mesh_x: 28,
      mesh_y: 48,
    };
  }
  if (sectionKey === "route_edges") {
    const from = nodes[0]?.facility_code || "";
    const to = nodes[1]?.facility_code || "";
    return {
      from_code: from,
      to_code: to,
      flow: "Editable material / proof flow",
      stage: "custom_link",
      evidence: `custom-link-${now}`,
      metric: "lead time | quantity | release status",
      quality_risk: "Editable risk note",
      temperature: "Editable temperature band",
      traceability: "Editable traceability rule",
    };
  }
  if (sectionKey === "evidence") {
    return {
      stage: "Editable proof stage",
      time: new Date().toISOString().slice(0, 10),
      location: "Editable location",
      item: detail?.overview?.product_name || "Editable item",
      evidence: `EV-${now}`,
      metric: "Editable metric",
      quality_risk: "Editable quality / risk",
      temp: "Editable temperature",
      trace: "Editable traceability",
      consumer_message: "Write the customer-facing proof message here.",
    };
  }
  return {};
}

function LayerEditor({ sku, detail, t, onSaved, setStatus }) {
  const sections = useMemo(() => [
    {
      key: "overview",
      label: t.admin.sections.overview,
      idField: "item_id",
      items: [{ ...detail.overview, item_id: "overview" }],
      fields: ["batch_code", "production_date", "expiry_date", "quality_score", "traceability_score", "plant_city", "qr_code"],
      labelOf: (item) => `${item.batch_code || "overview"} · ${item.plant_city || ""}`,
    },
    {
      key: "modules",
      label: t.admin.sections.modules,
      idField: "module_id",
      items: detail.modules,
      fields: ["module_name", "module_category", "supplier_city", "lot_code", "received_on", "inspection_score", "traceability_completeness", "temperature_excursion_minutes", "plain_language"],
      labelOf: (item) => `${moduleDisplayName(item)} · ${item.module_category || ""}`,
    },
    {
      key: "route_nodes",
      label: t.admin.sections.route_nodes,
      idField: "facility_code",
      items: detail.route.nodes,
      fields: ["stage", "paint_tag", "paint_color", "facility_code", "display_name", "facility_name", "facility_type", "city", "role", "visible_value", "mesh_x", "mesh_y"],
      labelOf: (item) => `${nodeTagLabel(item)} · ${nodeDisplayName(item)} · ${item.city || ""}`,
    },
    {
      key: "route_edges",
      label: t.admin.sections.route_edges,
      idField: "edge_id",
      items: detail.route.edges,
      fields: ["from_code", "to_code", "stage", "flow", "evidence", "metric", "quality_risk", "temperature", "traceability"],
      labelOf: (item) => `${nodeDisplayName(detail.route.nodes.find((node) => node.facility_code === item.from_code))} → ${nodeDisplayName(detail.route.nodes.find((node) => node.facility_code === item.to_code))}`,
    },
    {
      key: "evidence",
      label: t.admin.sections.evidence,
      idField: "evidence_id",
      items: detail.evidence,
      fields: ["stage", "time", "location", "item", "evidence", "metric", "quality_risk", "temp", "trace", "consumer_message"],
      labelOf: (item) => `${item.stage} · ${formatDate(item.time)} · ${item.evidence}`,
    },
  ], [detail, t]);

  const [sectionKey, setSectionKey] = useState("modules");
  const activeSection = sections.find((section) => section.key === sectionKey) || sections[0];
  const [selectedId, setSelectedId] = useState("");
  const currentItem = activeSection.items.find((item) => String(item[activeSection.idField]) === selectedId) || activeSection.items[0];
  const [draft, setDraft] = useState({});

  useEffect(() => {
    const ids = activeSection.items.map((item) => String(item[activeSection.idField]));
    if (!ids.length) {
      setSelectedId("");
    } else if (!ids.includes(selectedId)) {
      setSelectedId(ids[0]);
    }
  }, [sectionKey, detail, activeSection, selectedId]);

  useEffect(() => {
    const next = {};
    if (currentItem) {
      activeSection.fields.forEach((field) => {
        next[field] = currentItem[field] ?? "";
      });
    }
    setDraft(next);
  }, [currentItem, sectionKey]);

  const saveLayer = async () => {
    if (!currentItem) return;
    setStatus("Saving layer data...");
    await api(`/api/admin/products/${sku}/detail`, {
      method: "PATCH",
      body: JSON.stringify({
        section: activeSection.key,
        item_id: activeSection.key === "overview" ? null : String(currentItem[activeSection.idField]),
        updates: draft,
      }),
    });
    setStatus(t.admin.saved);
    await onSaved();
  };

  const createRecord = async () => {
    if (activeSection.key === "overview") return;
    setStatus("Creating record...");
    const result = await api(`/api/admin/products/${sku}/detail`, {
      method: "POST",
      body: JSON.stringify({
        section: activeSection.key,
        item: defaultDetailRecord(activeSection.key, detail),
      }),
    });
    setStatus("Created. You can rename it now.");
    await onSaved();
    setSelectedId(result.item_id);
  };

  const deleteRecord = async () => {
    if (activeSection.key === "overview" || !currentItem) return;
    const itemId = String(currentItem[activeSection.idField]);
    setStatus("Deleting record...");
    await api(`/api/admin/products/${sku}/detail/${activeSection.key}/${encodeURIComponent(itemId)}`, {
      method: "DELETE",
    });
    setSelectedId("");
    setStatus("Deleted. Customer page will refresh automatically.");
    await onSaved();
  };

  return (
    <section className="glass-card editor-panel layer-editor">
      <div className="section-heading">
        <span className="eyebrow">Layer editor</span>
        <h2>{t.admin.title}</h2>
      </div>
      <div className="section-tabs">
        {sections.map((section) => (
          <button
            key={section.key}
            className={section.key === sectionKey ? "active" : ""}
            onClick={() => setSectionKey(section.key)}
          >
            {section.label}
          </button>
        ))}
      </div>
      <div className="editor-actions">
        {activeSection.key !== "overview" && <button onClick={createRecord}>Add record</button>}
        {activeSection.key !== "overview" && currentItem && <button className="danger-action" onClick={deleteRecord}>Delete selected</button>}
      </div>
      {["route_nodes", "route_edges"].includes(sectionKey) && (
        <MeshEditor
          sku={sku}
          detail={detail}
          selectedId={selectedId}
          setSelectedId={setSelectedId}
          onSaved={onSaved}
          setStatus={setStatus}
          t={t}
        />
      )}
      <label className="field">
        <span>{t.admin.selectRecord}</span>
        <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)} disabled={!activeSection.items.length}>
          {activeSection.items.map((item) => (
            <option key={String(item[activeSection.idField])} value={String(item[activeSection.idField])}>
              {activeSection.labelOf(item)}
            </option>
          ))}
        </select>
      </label>
      <div className="form-grid dense-grid">
        {activeSection.fields.map((field) => (
          <EditableField
            key={field}
            label={fieldLabel(t, field)}
            value={draft[field] ?? ""}
            multiline={["plain_language", "visible_value", "consumer_message", "quality_risk", "metric"].includes(field)}
            onChange={(value) => setDraft({ ...draft, [field]: value })}
          />
        ))}
      </div>
      <button className="primary-action" onClick={saveLayer}>{t.admin.saveLayer}</button>
    </section>
  );
}

function MeshEditor({ sku, detail, selectedId, setSelectedId, onSaved, setStatus, t }) {
  const [nodes, setNodes] = useState(detail.route.nodes || []);
  const [connectFrom, setConnectFrom] = useState("");
  const [selectedEdgeId, setSelectedEdgeId] = useState("");
  const [selectedTag, setSelectedTag] = useState("Raw material");
  const [paintMode, setPaintMode] = useState(false);
  const [tagDraft, setTagDraft] = useState({ label: "", color: "#67e8f9" });
  const [editorOpen, setEditorOpen] = useState(false);

  useEffect(() => {
    setNodes(detail.route.nodes || []);
  }, [detail]);

  const edges = detail.route.edges || [];
  const selectedNode = nodes.find((node) => node.facility_code === selectedId) || nodes[0];
  const selectedEdge = edges.find((edge) => edgeKey(edge) === selectedEdgeId);
  const nodeMap = useMemo(() => new Map(nodes.map((node) => [nodeKey(node), node])), [nodes]);
  const tagPalette = useMemo(() => mergeTagPalettes(
    DEFAULT_TAGS,
    detail.overview?.flow_tags || [],
    nodes.map((node) => ({ label: nodeTagLabel(node), color: nodeAccentColor(node) })),
  ), [detail.overview?.flow_tags, nodes]);
  const activeTag = tagPalette.find((tag) => tag.label === selectedTag) || tagPalette[0] || DEFAULT_TAGS[0];

  useEffect(() => {
    if (!tagPalette.some((tag) => tag.label === selectedTag)) {
      setSelectedTag(tagPalette[0]?.label || DEFAULT_TAGS[0].label);
    }
  }, [tagPalette, selectedTag]);

  useEffect(() => {
    if (selectedEdgeId && !edges.some((edge) => edgeKey(edge) === selectedEdgeId)) {
      setSelectedEdgeId("");
    }
  }, [edges, selectedEdgeId]);

  const patchNode = async (node, updates) => {
    await api(`/api/admin/products/${sku}/detail`, {
      method: "PATCH",
      body: JSON.stringify({
        section: "route_nodes",
        item_id: String(node.facility_code),
        updates,
      }),
    });
  };

  const patchEdge = async (edge, updates) => {
    await api(`/api/admin/products/${sku}/detail`, {
      method: "PATCH",
      body: JSON.stringify({
        section: "route_edges",
        item_id: edgeKey(edge),
        updates,
      }),
    });
  };

  const patchOverview = async (updates) => {
    await api(`/api/admin/products/${sku}/detail`, {
      method: "PATCH",
      body: JSON.stringify({
        section: "overview",
        item_id: null,
        updates,
      }),
    });
  };

  const addNode = async () => {
    setStatus("Adding node...");
    const result = await api(`/api/admin/products/${sku}/detail`, {
      method: "POST",
      body: JSON.stringify({
        section: "route_nodes",
        item: defaultDetailRecord("route_nodes", detail),
      }),
    });
    setStatus("Node added. Rename it and drag it into place.");
    await onSaved();
    setSelectedId(result.item_id);
  };

  const deleteNode = async () => {
    if (!selectedNode) return;
    setSelectedEdgeId("");
    setStatus("Deleting node and connected links...");
    await api(`/api/admin/products/${sku}/detail/route_nodes/${encodeURIComponent(selectedNode.facility_code)}`, {
      method: "DELETE",
    });
    setSelectedId("");
    setStatus("Node deleted.");
    await onSaved();
  };

  const hasConnector = (fromCode, toCode, exceptEdgeId = "") => edges.some((edge) => (
    edgeKey(edge) !== exceptEdgeId
    && String(edge.from_code) === String(fromCode)
    && String(edge.to_code) === String(toCode)
  ));

  const hasConnectorPair = (fromCode, toCode, exceptEdgeId = "") => edges.some((edge) => {
    if (edgeKey(edge) === exceptEdgeId) return false;
    const edgeFrom = String(edge.from_code);
    const edgeTo = String(edge.to_code);
    return (
      (edgeFrom === String(fromCode) && edgeTo === String(toCode))
      || (edgeFrom === String(toCode) && edgeTo === String(fromCode))
    );
  });

  const deleteSelectedEdge = async () => {
    if (!selectedEdge) return;
    setStatus("Deleting selected connector...");
    await api(`/api/admin/products/${sku}/detail/route_edges/${encodeURIComponent(edgeKey(selectedEdge))}`, {
      method: "DELETE",
    });
    setSelectedEdgeId("");
    setStatus("Connector deleted.");
    await onSaved();
  };

  const reverseSelectedEdge = async () => {
    if (!selectedEdge) return;
    if (hasConnector(selectedEdge.to_code, selectedEdge.from_code, edgeKey(selectedEdge))) {
      setStatus("A connector with that direction already exists.");
      return;
    }
    const from = nodeMap.get(String(selectedEdge.to_code));
    const to = nodeMap.get(String(selectedEdge.from_code));
    setStatus("Reversing arrow direction...");
    try {
      await patchEdge(selectedEdge, {
        from_code: selectedEdge.to_code,
        to_code: selectedEdge.from_code,
        flow: `${nodeDisplayName(from)} to ${nodeDisplayName(to)}`,
        traceability: `${selectedEdge.to_code} -> ${selectedEdge.from_code}`,
      });
      setStatus("Arrow direction reversed.");
      await onSaved();
    } catch (error) {
      setStatus("A connector between those two nodes already exists.");
    }
  };

  const addEdge = async (fromCode, toCode) => {
    if (!fromCode || !toCode || fromCode === toCode) return;
    if (hasConnectorPair(fromCode, toCode)) {
      setStatus("Those two nodes are already connected. Select the line to reverse or delete it.");
      setConnectFrom("");
      return;
    }
    const from = nodeMap.get(fromCode);
    const to = nodeMap.get(toCode);
    setStatus("Creating link...");
    try {
      const result = await api(`/api/admin/products/${sku}/detail`, {
        method: "POST",
        body: JSON.stringify({
          section: "route_edges",
          item: {
            from_code: fromCode,
            to_code: toCode,
            flow: `${nodeDisplayName(from)} to ${nodeDisplayName(to)}`,
            stage: "merchant_drawn_link",
            evidence: `manual-link-${Date.now()}`,
            metric: "editable lead time | quantity | handoff status",
            quality_risk: "editable risk, release, or exception note",
            temperature: "editable temperature band",
            traceability: "merchant-defined relationship",
          },
        }),
      });
      setConnectFrom("");
      setSelectedEdgeId(result.item_id || "");
      setStatus("Link created.");
      await onSaved();
    } catch (error) {
      setConnectFrom("");
      setStatus("Those two nodes are already connected.");
    }
  };

  const createTag = async () => {
    const label = tagDraft.label.trim();
    if (!label) return;
    const nextTag = { label, color: tagDraft.color || "#67e8f9" };
    const nextTags = mergeTagPalettes(detail.overview?.flow_tags || [], tagPalette, nextTag);
    setStatus("Saving tag...");
    await patchOverview({ flow_tags: nextTags });
    setSelectedTag(label);
    setTagDraft({ label: "", color: nextTag.color });
    setStatus("Tag saved. Paint nodes with it from the full-screen editor.");
    await onSaved();
  };

  const paintNode = async (node) => {
    if (!node || !activeTag) return;
    await paintNodeWithTag(node, activeTag);
  };

  const paintNodeWithTag = async (node, tag) => {
    const normalized = normalizeTag(tag);
    if (!node || !normalized) return;
    const code = nodeKey(node);
    setNodes((current) => current.map((item) => (
      nodeKey(item) === code ? { ...item, paint_tag: normalized.label, paint_color: normalized.color } : item
    )));
    setStatus(`Painting ${nodeDisplayName(node)} as ${normalized.label}...`);
    await patchNode(node, { paint_tag: normalized.label, paint_color: normalized.color });
    setSelectedId(code);
    setSelectedEdgeId("");
    setSelectedTag(normalized.label);
    setStatus("Node tag applied.");
    await onSaved();
  };

  const handleNodeClick = async (node) => {
    const code = nodeKey(node);
    setSelectedEdgeId("");
    if (paintMode) {
      await paintNode(node);
      return;
    }
    if (!connectFrom) {
      setSelectedId(code);
      return;
    }
    await addEdge(connectFrom, code);
  };

  const moveNode = (code, point) => {
    setSelectedEdgeId("");
    setNodes((current) => current.map((node) => (
      nodeKey(node) === code ? { ...node, mesh_px_x: point.x, mesh_px_y: point.y, layout_locked: true } : node
    )));
  };

  const saveNodePosition = async (code, point) => {
    const node = nodes.find((item) => nodeKey(item) === code);
    if (!node || point.x == null || point.y == null) return;
    setStatus("Saving node position...");
    await patchNode(node, {
      mesh_px_x: Number(point.x).toFixed(2),
      mesh_px_y: Number(point.y).toFixed(2),
      layout_locked: true,
    });
    setStatus("Node position saved.");
    await onSaved();
  };

  const autoLayoutNodes = async () => {
    if (!nodes.length) return;
    setStatus("Applying automatic layout...");
    const layout = buildDiagramLayout(nodes, { preferSaved: false, routeLayout: detail.route.layout });
    setNodes(layout.nodes.map((node) => ({ ...node, layout_locked: false })));
    await Promise.all(layout.nodes.map((node) => patchNode(node, {
      mesh_px_x: Number(node.mesh_px_x).toFixed(2),
      mesh_px_y: Number(node.mesh_px_y).toFixed(2),
      layout_locked: false,
    })));
    setStatus("Automatic layout applied.");
    await onSaved();
  };

  const renderToolbar = (insideModal = false) => (
    <div className="mesh-toolbar">
      <button type="button" onClick={addNode}>Add node</button>
      <button
        type="button"
        className={connectFrom ? "active" : ""}
        onClick={() => setConnectFrom(connectFrom ? "" : nodeKey(selectedNode))}
        disabled={!selectedNode}
      >
        {connectFrom ? "Pick target node" : "Connect from selected"}
      </button>
      <button type="button" onClick={autoLayoutNodes}>Auto layout</button>
      <button type="button" onClick={reverseSelectedEdge} disabled={!selectedEdge}>Reverse arrow</button>
      <button type="button" className="danger-action" onClick={deleteSelectedEdge} disabled={!selectedEdge}>Delete line</button>
      {!insideModal && (
        <button
          type="button"
          onClick={() => {
            requestBrowserFullscreen();
            setEditorOpen(true);
          }}
        >
          Full-screen edit
        </button>
      )}
      <button type="button" className="danger-action" onClick={deleteNode} disabled={!selectedNode}>Delete node</button>
    </div>
  );

  const renderTagTools = () => (
    <div className="tag-toolbar">
      <div className="tag-palette" aria-label="Node tags">
        {tagPalette.map((tag) => (
          <button
            type="button"
            draggable
            key={tag.label}
            className={selectedTag === tag.label ? "active" : ""}
            onClick={() => setSelectedTag(tag.label)}
            onDragStart={(event) => {
              event.dataTransfer.effectAllowed = "copy";
              event.dataTransfer.setData("application/json", JSON.stringify(tag));
              event.dataTransfer.setData("text/plain", tag.label);
            }}
          >
            <span style={{ background: tag.color }} />
            {tag.label}
          </button>
        ))}
      </div>
      <div className="tag-create">
        <input
          value={tagDraft.label}
          placeholder="New tag"
          onChange={(event) => setTagDraft({ ...tagDraft, label: event.target.value })}
        />
        <input
          type="color"
          value={tagDraft.color}
          aria-label="Tag color"
          onChange={(event) => setTagDraft({ ...tagDraft, color: event.target.value })}
        />
        <button type="button" onClick={createTag}>Add tag</button>
        <button type="button" className={paintMode ? "active" : ""} onClick={() => setPaintMode(!paintMode)}>
          {paintMode ? "Painting" : "Paint nodes"}
        </button>
      </div>
    </div>
  );

  const inspector = (
    <aside className="fullscreen-inspector editor-inspector">
      <NodeDetail node={selectedNode} t={t} />
      <div className="selected-edge-panel">
        <span className="eyebrow">Selected connector</span>
        {selectedEdge ? (
          <>
            <strong>{nodeDisplayName(nodeMap.get(String(selectedEdge.from_code)))} → {nodeDisplayName(nodeMap.get(String(selectedEdge.to_code)))}</strong>
            <p>{selectedEdge.flow || selectedEdge.metric || "Editable flow connector"}</p>
            <div className="line-actions">
              <button type="button" onClick={reverseSelectedEdge}>Reverse arrow</button>
              <button type="button" className="danger-action" onClick={deleteSelectedEdge}>Delete line</button>
            </div>
          </>
        ) : (
          <p>Drag a connector handle to draw a line, or click an existing line to edit its direction.</p>
        )}
      </div>
      <div className="editor-edge-list">
        <span className="eyebrow">Visible links</span>
        {edges.slice(0, 10).map((edge) => (
          <button
            key={edgeKey(edge)}
            type="button"
            className={selectedEdgeId === edgeKey(edge) ? "active" : ""}
            onClick={() => setSelectedEdgeId(edgeKey(edge))}
          >
            <strong>{nodeDisplayName(nodeMap.get(String(edge.from_code)))}</strong>
            <span>{nodeDisplayName(nodeMap.get(String(edge.to_code)))}</span>
          </button>
        ))}
      </div>
    </aside>
  );

  const activeNodeCode = selectedNode ? nodeKey(selectedNode) : "";

  useEffect(() => {
    if (!editorOpen) return undefined;
    const handleKeyDown = (event) => {
      if (isTypingTarget(event.target)) return;
      const key = event.key.toLowerCase();
      if (key === "delete" || key === "backspace") {
        event.preventDefault();
        if (selectedEdge) {
          deleteSelectedEdge();
        } else {
          deleteNode();
        }
      }
      if (event.ctrlKey && key === "r") {
        event.preventDefault();
        reverseSelectedEdge();
      }
      if (event.ctrlKey && key === "l") {
        event.preventDefault();
        setConnectFrom(connectFrom ? "" : activeNodeCode);
      }
      if (event.ctrlKey && key === "a") {
        event.preventDefault();
        autoLayoutNodes();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [editorOpen, selectedEdge, selectedNode, connectFrom, activeNodeCode]);

  return (
    <div className="mesh-editor">
      {renderToolbar(false)}
      {renderTagTools()}
      <DiagramCanvas
        route={detail.route}
        nodes={nodes}
        edges={edges}
        activeNodeCode={activeNodeCode}
        onNodeSelect={handleNodeClick}
        onTagDrop={paintNodeWithTag}
        selectedEdgeId={selectedEdgeId}
        onEdgeSelect={(edge) => {
          setSelectedEdgeId(edgeKey(edge));
          setConnectFrom("");
        }}
        connectFrom={connectFrom}
        className="diagram-admin-preview"
        fitPadding={24}
      />
      {editorOpen && (
        <FullScreenModal title="Professional flow editor" subtitle="Merchant backend" onClose={() => setEditorOpen(false)}>
          <div className="fullscreen-content editor-content">
            <section className="fullscreen-diagram-panel">
              {renderToolbar(true)}
              {renderTagTools()}
              <DiagramCanvas
                route={detail.route}
                nodes={nodes}
                edges={edges}
                activeNodeCode={activeNodeCode}
                onNodeSelect={handleNodeClick}
                onTagDrop={paintNodeWithTag}
                selectedEdgeId={selectedEdgeId}
                onEdgeSelect={(edge) => {
                  setSelectedEdgeId(edgeKey(edge));
                  setConnectFrom("");
                }}
                onConnectNodes={addEdge}
                editable
                connectFrom={connectFrom}
                onNodeDrag={moveNode}
                onNodeDragEnd={saveNodePosition}
                className="diagram-editor-full"
                fitPadding={72}
              />
            </section>
            {inspector}
          </div>
        </FullScreenModal>
      )}
      <p className="mesh-help">
        Canvas logic: add checkpoints, drag nodes to reshape the mesh, then connect two nodes to express supplier, QC, packaging, logistics, or retail handoffs.
      </p>
    </div>
  );
}

function Input({ label, value, onChange, type = "text" }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type={type} value={value ?? ""} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function EditableField({ label, value, onChange, multiline = false }) {
  return (
    <label className={`field ${multiline ? "wide-field" : ""}`}>
      <span>{label}</span>
      {multiline ? (
        <textarea value={value ?? ""} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <input value={value ?? ""} onChange={(event) => onChange(event.target.value)} />
      )}
    </label>
  );
}

function MediaEditor({ sku, slot, onSaved, setStatus, t }) {
  const [url, setUrl] = useState(slot.url || "");

  useEffect(() => {
    setUrl(slot.url || "");
  }, [slot.url]);

  const saveUrl = async () => {
    setStatus(`Saving ${slot.slot} URL...`);
    await api(`/api/admin/products/${sku}/media/${slot.media_key}`, {
      method: "PUT",
      body: JSON.stringify({ url }),
    });
    setStatus(`${slot.slot} saved.`);
    onSaved();
  };

  const upload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setStatus(`Uploading ${slot.slot}...`);
    await api(`/api/admin/products/${sku}/media/${slot.media_key}/upload`, {
      method: "POST",
      body: formData,
    });
    setStatus(`${slot.slot} uploaded.`);
    onSaved();
  };

  return (
    <div className="media-editor-card">
      <div className="media-preview">
        {slot.url ? <img src={mediaUrl(slot.url)} alt={slot.slot} /> : <IconPlaceholder label={slot.slot} />}
      </div>
      <div>
        <h3>{slot.slot}</h3>
        <p>{slot.why}</p>
        <input value={url} placeholder={slot.interface_key} onChange={(event) => setUrl(event.target.value)} />
        <div className="media-actions">
          <button onClick={saveUrl}>{t.admin.saveUrl}</button>
          <label>
            {t.admin.upload}
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={upload} />
          </label>
        </div>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
