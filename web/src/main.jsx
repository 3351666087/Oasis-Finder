import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "";
const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/updates`;

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
  const isAdmin = location.pathname.startsWith("/admin");
  return isAdmin ? <MerchantStudio /> : <ConsumerExperience />;
}

function ConsumerExperience() {
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
      <TopNav mode="consumer" />
      <main className="glass-page">
        <Hero selectedProduct={selectedProduct} />
        <CustomerGuide />
        <section className="product-rail">
          {products.map((product) => (
            <button
              className={`product-tile ${product.sku_code === selectedSku ? "active" : ""}`}
              key={product.sku_code}
              onClick={() => setSelectedSku(product.sku_code)}
            >
              <MediaThumb product={product} />
              <span className="tile-category">{product.category_label}</span>
              <strong>{product.product_name}</strong>
              <span>RMB {Number(product.unit_price).toFixed(2)} · proof {Number(product.proof_score).toFixed(1)}</span>
            </button>
          ))}
        </section>

        {loading || !detail ? (
          <div className="glass-card loading-card">Loading product journey...</div>
        ) : (
          <section className="split-layout">
            <ProductDissection
              detail={detail}
              selectedModule={selectedModule}
              setSelectedModule={setSelectedModule}
            />
            <RouteExplorer route={route} selectedModule={selectedModule} detail={detail} />
          </section>
        )}
      </main>
    </div>
  );
}

function TopNav({ mode }) {
  return (
    <header className="top-nav">
      <div>
        <span className="brand-mark">OF</span>
        <span className="brand-name">Oasis Finder</span>
      </div>
      <nav>
        <a className={mode === "consumer" ? "active" : ""} href="/">Customer view</a>
        <a className={mode === "admin" ? "active" : ""} href="/admin">Merchant studio</a>
        <a href="http://127.0.0.1:8000/docs">API docs</a>
      </nav>
    </header>
  );
}

function Hero({ selectedProduct }) {
  return (
    <section className="hero-grid">
      <div className="hero-copy">
        <span className="eyebrow">Fresh-food transparency layer</span>
        <h1>Pick a product, then inspect the chain behind it.</h1>
        <p>
          Shoppers see the product first. One click breaks the product into components, route stages,
          proof images, time, place, quality, and cold-chain evidence.
        </p>
      </div>
      <div className="hero-metric">
        <span>Selected SKU</span>
        <strong>{selectedProduct?.sku_code || "--"}</strong>
        <p>{selectedProduct?.consumer_claim || "Real-time merchant updates appear here."}</p>
      </div>
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

function ProductDissection({ detail, selectedModule, setSelectedModule }) {
  const overview = detail.overview;
  return (
    <section className="glass-card dissection-card">
      <div className="section-heading">
        <span className="eyebrow">Module dissection</span>
        <h2>{overview.product_name}</h2>
        <p>像把蛋糕拆成蛋糕胚和奶油一样，这里把商品拆成可点击的供应链模块。</p>
      </div>

      <div className="dissection-stage">
        <button
          className={`core-product ${selectedModule === "whole" ? "active" : ""}`}
          onClick={() => setSelectedModule("whole")}
        >
          <span>Whole product</span>
          <strong>{overview.product_name}</strong>
          <small>{overview.batch_code} · trace {Number(overview.traceability_score || 0).toFixed(1)}%</small>
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

function RouteExplorer({ route, selectedModule, detail }) {
  const nodes = route?.nodes || [];
  const edges = route?.edges || [];
  const selectedModulePayload = detail.modules.find((module) => module.module_id === selectedModule);
  const groups = useMemo(() => {
    const order = ["Ingredient source", "Processing / packing", "Distribution center", "Retail shelf", "Logistics node"];
    return order
      .map((stage) => ({ stage, nodes: nodes.filter((node) => node.stage === stage) }))
      .filter((group) => group.nodes.length);
  }, [nodes]);

  const evidence = selectedModule === "whole"
    ? detail.evidence.slice(0, 5)
    : selectedModulePayload?.plain_language;
  const variableSet = selectedModule === "whole"
    ? [
        ["Batch", detail.overview.batch_code],
        ["Production date", detail.overview.production_date],
        ["Expiry date", detail.overview.expiry_date],
        ["Storage", detail.overview.storage_temp_band],
        ["Quality", Number(detail.overview.quality_score || 0).toFixed(1)],
        ["QR", detail.overview.qr_code],
      ]
    : [
        ["Module", selectedModulePayload?.module_name],
        ["Supplier city", selectedModulePayload?.supplier_city],
        ["Lot", selectedModulePayload?.lot_code],
        ["Received", selectedModulePayload?.received_on],
        ["Inspection", Number(selectedModulePayload?.inspection_score || 0).toFixed(1)],
        ["Traceability", `${(Number(selectedModulePayload?.traceability_completeness || 0) * 100).toFixed(1)}%`],
      ];

  return (
    <section className="glass-card route-card">
      <div className="section-heading">
        <span className="eyebrow">Animated route switch</span>
        <h2>{selectedModule === "whole" ? "Whole-product supply chain" : "Selected module supply chain"}</h2>
        <p>切换整品或元件时，路线会平滑过渡，用户知道自己正在看哪一层证据。</p>
      </div>
      <div className="route-canvas" key={selectedModule}>
        {groups.map((group, index) => (
          <div className="route-stage" key={group.stage}>
            <h3>{group.stage}</h3>
            {group.nodes.map((node) => (
              <div className="route-node" key={node.facility_code}>
                <strong>{node.facility_code}</strong>
                <span>{node.city} · {node.role}</span>
              </div>
            ))}
            {index < groups.length - 1 && <div className="route-arrow">→</div>}
          </div>
        ))}
      </div>
      <EvidenceMatrix variables={variableSet} />
      <div className="proof-panel">
        <h3>What the shopper learns</h3>
        {typeof evidence === "string" ? (
          <p>{evidence}</p>
        ) : Array.isArray(evidence) && evidence.length ? (
          evidence.map((row) => (
            <p key={`${row.stage}-${row.evidence}`}>
              <strong>{row.stage}</strong> · {row.time} · {row.metric}
            </p>
          ))
        ) : (
          <p>Select a product component to see its supplier lot, route, and evidence variables.</p>
        )}
        <span className="edge-count">{edges.length} flow links visible in this view</span>
      </div>
    </section>
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

function MerchantStudio() {
  const [products, setProducts] = useState([]);
  const [selectedSku, setSelectedSku] = useState("");
  const [detail, setDetail] = useState(null);
  const [form, setForm] = useState({});
  const [status, setStatus] = useState("Ready");

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
    setStatus(`Live update received: ${event.type}`);
    loadProducts();
    if (event.sku_code === selectedSku) loadDetail(selectedSku);
  });

  const saveProduct = async () => {
    setStatus("Saving product data...");
    await api(`/api/admin/products/${selectedSku}`, { method: "PATCH", body: JSON.stringify(form) });
    setStatus("Saved. Customer page will refresh automatically.");
  };

  return (
    <div className="app-shell admin-bg">
      <TopNav mode="admin" />
      <main className="admin-layout">
        <aside className="glass-card admin-sidebar">
          <span className="eyebrow">Merchant backend</span>
          <h1>Edit product data and images</h1>
          <p>这里是给商家看的后台。改完数据或图片后，用户前台会收到实时更新。</p>
          <AdminWorkflow />
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
          <section className="glass-card editor-panel">
            <div className="section-heading">
              <span className="eyebrow">Data editor</span>
              <h2>{detail.overview.product_name}</h2>
              <p>Step 1: edit the product data. Step 2: upload or paste proof images. Step 3: open the customer page to watch it update.</p>
            </div>
            <div className="form-grid">
              <Input label="Product name" value={form.product_name} onChange={(v) => setForm({ ...form, product_name: v })} />
              <Input label="Category" value={form.category} onChange={(v) => setForm({ ...form, category: v })} />
              <Input label="Unit price" type="number" value={form.unit_price} onChange={(v) => setForm({ ...form, unit_price: Number(v) })} />
              <Input label="Shelf life days" type="number" value={form.shelf_life_days} onChange={(v) => setForm({ ...form, shelf_life_days: Number(v) })} />
              <Input label="Storage temp band" value={form.storage_temp_band} onChange={(v) => setForm({ ...form, storage_temp_band: v })} />
            </div>
            <button className="primary-action" onClick={saveProduct}>Save product data</button>

            <div className="media-editor-grid">
              {detail.media_slots.map((slot) => (
                <MediaEditor
                  key={slot.media_key}
                  sku={selectedSku}
                  slot={slot}
                  onSaved={() => loadDetail(selectedSku)}
                  setStatus={setStatus}
                />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function CustomerGuide() {
  return (
    <section className="guide-row" aria-label="How customers use Oasis Finder">
      <div>
        <span>1</span>
        <strong>先选商品</strong>
        <p>像山姆或盒马 App 一样，从名称、类别和价格进入。</p>
      </div>
      <div>
        <span>2</span>
        <strong>再拆元件</strong>
        <p>整品路线保留，蛋糕胚、奶油等模块可以单独点开。</p>
      </div>
      <div>
        <span>3</span>
        <strong>看证据再买</strong>
        <p>时间、地点、批次、温控和质检变成可读的购买理由。</p>
      </div>
    </section>
  );
}

function AdminWorkflow() {
  return (
    <div className="admin-workflow" aria-label="Merchant workflow">
      <span>Merchant flow</span>
      <p>选择 SKU → 改商品数据 → 上传图片证据 → 前台实时刷新。</p>
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

function MediaEditor({ sku, slot, onSaved, setStatus }) {
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
    setStatus(`${slot.slot} saved. Customer page will refresh.`);
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
    setStatus(`${slot.slot} uploaded. Customer page will refresh.`);
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
          <button onClick={saveUrl}>Save URL</button>
          <label>
            Upload image
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={upload} />
          </label>
        </div>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
