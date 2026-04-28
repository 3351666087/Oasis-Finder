import React, { useEffect, useMemo, useState } from "react";
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
    routeHint: "筛选 L1 / L2 / L3 / CORE 等层级，点击节点可查看更直观的阶段数据。",
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
      flow: "选择 SKU → 编辑商品 → 编辑 L1/L2/L3/CORE 节点 → 上传图片 → 前台刷新",
      ready: "就绪",
      dataEditor: "商品基础数据",
      dataHint: "第 1 步：编辑商品基础字段。第 2 步：编辑每个层级。第 3 步：上传图片证据。",
      saveProduct: "保存商品基础数据",
      saved: "已保存，客户前台将自动刷新。",
      sections: {
        overview: "整品/批次",
        modules: "商品元件",
        route_nodes: "L1/L2/L3/节点",
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
      supplier_tier: "供应商层级",
      supplier_city: "供应商城市",
      lot_code: "批号",
      received_on: "入厂日期",
      inspection_score: "检验分",
      traceability_completeness: "追溯完整度",
      temperature_excursion_minutes: "温度偏离分钟",
      plain_language: "客户可读说明",
      stage: "阶段",
      tier: "层级",
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
    routeHint: "Filter L1 / L2 / L3 / CORE layers, then click a node to see clearer stage data.",
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
      flow: "Select SKU → edit product → edit L1/L2/L3/CORE nodes → upload images → frontend refreshes",
      ready: "Ready",
      dataEditor: "Product data editor",
      dataHint: "Step 1: edit product fields. Step 2: edit every layer. Step 3: upload evidence images.",
      saveProduct: "Save product data",
      saved: "Saved. Customer page will refresh automatically.",
      sections: {
        overview: "Whole product / batch",
        modules: "Product modules",
        route_nodes: "L1/L2/L3 nodes",
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
      supplier_tier: "Supplier tier",
      supplier_city: "Supplier city",
      lot_code: "Lot code",
      received_on: "Received on",
      inspection_score: "Inspection score",
      traceability_completeness: "Traceability completeness",
      temperature_excursion_minutes: "Temperature excursion minutes",
      plain_language: "Plain-language message",
      stage: "Stage",
      tier: "Tier",
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
    : { nodes: selectedModulePayload?.route_nodes || [], edges: selectedModulePayload?.route_edges || [] };

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
              <strong>{module.module_name}</strong>
              <small>{module.supplier_tier || "L?"} · {module.supplier_city || "mapped supplier"} · score {Number(module.module_score || 0).toFixed(1)}</small>
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

function RouteExplorer({ route, selectedModule, detail, t }) {
  const nodes = route?.nodes || [];
  const edges = route?.edges || [];
  const selectedModulePayload = detail.modules.find((module) => module.module_id === selectedModule);
  const layerOptions = useMemo(() => ["ALL", ...Array.from(new Set(nodes.map((node) => node.tier).filter(Boolean)))], [nodes]);
  const [layer, setLayer] = useState("ALL");
  const [activeNodeCode, setActiveNodeCode] = useState("");

  useEffect(() => {
    setLayer("ALL");
    setActiveNodeCode("");
  }, [selectedModule]);

  const filteredNodes = layer === "ALL" ? nodes : nodes.filter((node) => node.tier === layer);
  const activeNode = filteredNodes.find((node) => node.facility_code === activeNodeCode) || filteredNodes[0];
  const groups = useMemo(() => {
    const order = ["Ingredient source", "Processing / packing", "Distribution center", "Retail shelf", "Logistics node"];
    return order
      .map((stage) => ({ stage, nodes: filteredNodes.filter((node) => node.stage === stage) }))
      .filter((group) => group.nodes.length);
  }, [filteredNodes]);

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
        [t.variables.module, selectedModulePayload?.module_name],
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
          <button key={option} className={layer === option ? "active" : ""} onClick={() => setLayer(option)}>
            {option === "ALL" ? t.layerAll : option}
          </button>
        ))}
      </div>
      <div className="route-canvas" key={`${selectedModule}-${layer}`}>
        {groups.map((group, index) => (
          <div className="route-stage" key={group.stage}>
            <h3>{group.stage}</h3>
            {group.nodes.map((node) => (
              <button
                className={`route-node ${activeNode?.facility_code === node.facility_code ? "active" : ""}`}
                key={node.facility_code}
                onClick={() => setActiveNodeCode(node.facility_code)}
              >
                <strong>{node.facility_code}</strong>
                <span>{node.tier} · {node.city} · {node.role}</span>
              </button>
            ))}
            {index < groups.length - 1 && <div className="route-arrow">→</div>}
          </div>
        ))}
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
        <span className="edge-count">{edges.length} {t.flowLinks}</span>
      </div>
    </section>
  );
}

function NodeDetail({ node, t }) {
  if (!node) return null;
  return (
    <div className="node-detail-panel">
      <div>
        <span>{t.nodeDetail}</span>
        <strong>{node.facility_name || node.facility_code}</strong>
      </div>
      <p>{node.visible_value || t.nodeHint}</p>
      <div className="node-detail-grid">
        <small>{fieldLabel(t, "tier")}: {node.tier || "--"}</small>
        <small>{fieldLabel(t, "city")}: {node.city || "--"}</small>
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
      fields: ["module_name", "module_category", "supplier_tier", "supplier_city", "lot_code", "received_on", "inspection_score", "traceability_completeness", "temperature_excursion_minutes", "plain_language"],
      labelOf: (item) => `${item.module_id} · ${item.module_name}`,
    },
    {
      key: "route_nodes",
      label: t.admin.sections.route_nodes,
      idField: "facility_code",
      items: detail.route.nodes,
      fields: ["stage", "tier", "facility_code", "facility_name", "facility_type", "city", "role", "visible_value"],
      labelOf: (item) => `${item.tier || "L?"} · ${item.facility_code} · ${item.city || ""}`,
    },
    {
      key: "route_edges",
      label: t.admin.sections.route_edges,
      idField: "edge_id",
      items: detail.route.edges,
      fields: ["from_code", "to_code", "flow", "evidence", "metric", "quality_risk", "temperature", "traceability"],
      labelOf: (item) => `${item.from_code} → ${item.to_code}`,
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
    setSelectedId(String(activeSection.items[0]?.[activeSection.idField] || ""));
  }, [sectionKey, detail]);

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
    onSaved();
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
      <label className="field">
        <span>{t.admin.selectRecord}</span>
        <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
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
