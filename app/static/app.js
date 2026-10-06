"use strict";

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

const $ = (sel, root = document) => root.querySelector(sel);
const NF = new Intl.NumberFormat("es-ES");
const NF2 = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 2 });
const USD = new Intl.NumberFormat("es-ES", { style: "currency", currency: "USD", maximumFractionDigits: 4 });

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const isNum = (v) => typeof v === "number" && Number.isFinite(v);
// Un dato ausente se muestra vacío: nunca se inventa.
const num = (v) => (isNum(v) ? NF.format(v) : "");
const dec = (v) => (isNum(v) ? NF2.format(v) : "");
const money = (v) => (isNum(v) ? USD.format(v) : "");
const pct = (v) => (isNum(v) ? `${NF2.format(v * 100)} %` : "");
const yesno = (v) => (v === true ? "Sí" : v === false ? "No" : "");
const get = (obj, path) => path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);

function link(url) {
  if (typeof url !== "string" || !/^https?:\/\//i.test(url)) return esc(url ?? "");
  return `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(url)}</a>`;
}

function sparkline(monthly) {
  if (!Array.isArray(monthly) || monthly.length < 2) return "";
  const pts = monthly
    .filter((m) => isNum(m.search_volume))
    .sort((a, b) => a.year - b.year || a.month - b.month)
    .map((m) => m.search_volume);
  if (pts.length < 2) return "";
  const w = 80, h = 20, max = Math.max(...pts), min = Math.min(...pts);
  const span = max - min || 1;
  const coords = pts.map((v, i) => `${(i / (pts.length - 1)) * w},${h - ((v - min) / span) * (h - 2) - 1}`).join(" ");
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${coords}"/></svg>`;
}

// ---------------------------------------------------------------------------
// Llamadas a la API con confirmación de coste
// ---------------------------------------------------------------------------

const geo = () => {
  const loc = parseInt($("#geo-location").value, 10);
  const lang = $("#geo-language").value.trim();
  return { location_code: Number.isFinite(loc) ? loc : null, language_code: lang || null };
};

function askConfirm(err) {
  const dialog = $("#confirm-dialog");
  const est = isNum(err.estimated_cost)
    ? `<br>Coste estimado: <b>${money(err.estimated_cost)}</b> (umbral: ${money(err.threshold)}).`
    : "<br>El coste real quedará registrado y se usará para estimar las próximas consultas.";
  $("#confirm-text").innerHTML = `${esc(err.message)}<br><br>Endpoint: <code>${esc(err.endpoint)}</code>${est}`;
  dialog.returnValue = "";
  dialog.showModal();
  return new Promise((resolve) => dialog.addEventListener("close", () => resolve(dialog.returnValue === "ok"), { once: true }));
}

async function api(method, path, body, confirm = false) {
  const url = new URL(path, location.origin);
  if (confirm) url.searchParams.set("confirm", "true");
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch { /* sin cuerpo */ }
  if (res.ok) return data;
  if (res.status === 402 && data?.error === "confirmation_required" && !confirm) {
    if (await askConfirm(data)) return api(method, path, body, true);
    throw new Error("Consulta cancelada: no se ha gastado crédito.");
  }
  let msg = data?.message;
  if (!msg && Array.isArray(data?.detail)) msg = data.detail.map((d) => `${d.loc?.slice(1).join(".")}: ${d.msg}`).join("; ");
  throw new Error(msg || `Error HTTP ${res.status}`);
}

// ---------------------------------------------------------------------------
// Componentes de salida
// ---------------------------------------------------------------------------

function metaLine(meta, extra = "") {
  if (!meta) return "";
  const parts = [];
  if (meta.from_cache) {
    const when = meta.cached_at ? new Date(meta.cached_at * 1000).toLocaleString("es-ES") : "";
    parts.push(`<span class="tag">Desde caché ${esc(when)} · sin coste</span>`);
  } else if (meta.endpoint !== "local") {
    parts.push(`<span class="tag">Coste real: ${isNum(meta.cost) ? money(meta.cost) : "no informado"}</span>`);
  }
  if (meta.endpoint && meta.endpoint !== "local") parts.push(`<span>${esc(meta.endpoint)}</span>`);
  if (extra) parts.push(extra);
  return `<div class="meta">${parts.join("")}</div>`;
}

function cards(list) {
  return `<div class="cards">${list
    .map((c) => `<div class="card"><div class="label">${esc(c.label)}</div><div class="value ${c.cls || ""}">${c.value === "" || c.value == null ? "&nbsp;" : c.value}</div></div>`)
    .join("")}</div>`;
}

let tableSeq = 0;
const tables = new Map();

/** cols: [{key, label, fmt?, num?, cls?, csv?}] — key admite rutas "a.b.c" */
function table(cols, rows, title = "") {
  const id = `t${++tableSeq}`;
  tables.set(id, { cols, rows: rows || [], sort: null });
  return `<div class="table-wrap" id="${id}">${tableInner(id, title)}</div>`;
}

function tableInner(id, title) {
  const t = tables.get(id);
  const head = t.cols.map((c, i) => `<th data-col="${i}" class="${c.num ? "num" : ""}">${esc(c.label)}${t.sort?.i === i ? (t.sort.dir > 0 ? " ▲" : " ▼") : ""}</th>`).join("");
  const body = t.rows.length
    ? t.rows.map((r) => `<tr>${t.cols.map((c) => {
        const v = get(r, c.key);
        const html = c.fmt ? c.fmt(v, r) : esc(v ?? "");
        return `<td class="${c.num ? "num" : ""} ${c.cls || ""}">${html}</td>`;
      }).join("")}</tr>`).join("")
    : `<tr><td colspan="${t.cols.length}" class="muted">Sin resultados.</td></tr>`;
  return `<div class="table-tools"><span>${esc(title)} ${NF.format(t.rows.length)} filas</span>
    <button type="button" class="small secondary" data-csv="${id}">Exportar CSV</button></div>
    <table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

document.addEventListener("click", (ev) => {
  const th = ev.target.closest("th[data-col]");
  if (th) {
    const wrap = th.closest(".table-wrap");
    const t = tables.get(wrap.id);
    const i = Number(th.dataset.col);
    const dir = t.sort?.i === i ? -t.sort.dir : (t.cols[i].num ? -1 : 1);
    t.sort = { i, dir };
    const key = t.cols[i].key;
    t.rows.sort((a, b) => {
      const x = get(a, key), y = get(b, key);
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return (x > y ? 1 : x < y ? -1 : 0) * dir;
    });
    const title = wrap.querySelector(".table-tools span").textContent.replace(/[\d.]+ filas$/, "").trim();
    wrap.innerHTML = tableInner(wrap.id, title);
    return;
  }
  const csvBtn = ev.target.closest("[data-csv]");
  if (csvBtn) exportCsv(csvBtn.dataset.csv);
});

function exportCsv(id) {
  const t = tables.get(id);
  const cell = (v) => {
    if (v == null) return "";
    if (Array.isArray(v)) v = v.map((x) => (typeof x === "object" ? JSON.stringify(x) : x)).join(" | ");
    else if (typeof v === "object") v = JSON.stringify(v);
    const s = String(v);
    return /[",;\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [t.cols.map((c) => cell(c.label)).join(",")];
  for (const r of t.rows) lines.push(t.cols.map((c) => cell(c.csv ? c.csv(get(r, c.key), r) : get(r, c.key))).join(","));
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `sniplyze-${currentTool?.id || "datos"}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function bars(rows) {
  const max = Math.max(1, ...rows.map((r) => (isNum(r.value) ? r.value : 0)));
  return `<div class="bars">${rows
    .map((r) => `<div class="bar-row"><span>${esc(r.label)}</span><div class="bar-track"><div class="bar-fill" style="width:${isNum(r.value) ? (r.value / max) * 100 : 0}%"></div></div><span class="num">${num(r.value)}</span></div>`)
    .join("")}</div>`;
}

function lineChart(points, label) {
  const pts = points.filter((p) => isNum(p.y));
  if (pts.length < 2) return "";
  const W = 640, H = 200, P = 36;
  const max = Math.max(...pts.map((p) => p.y)), min = Math.min(0, ...pts.map((p) => p.y));
  const span = max - min || 1;
  const x = (i) => P + (i / (pts.length - 1)) * (W - 2 * P);
  const y = (v) => H - P - ((v - min) / span) * (H - 2 * P);
  const step = Math.max(1, Math.ceil(pts.length / 8));
  const labels = pts.map((p, i) => (i % step === 0 ? `<text x="${x(i)}" y="${H - 10}" text-anchor="middle">${esc(p.x)}</text>` : "")).join("");
  return `<div class="chart"><h3>${esc(label)}</h3><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">
    <line class="axis" x1="${P}" y1="${H - P}" x2="${W - P}" y2="${H - P}"/>
    <text x="${P - 4}" y="${y(max) + 4}" text-anchor="end">${esc(NF.format(Math.round(max)))}</text>
    <text x="${P - 4}" y="${y(min) + 4}" text-anchor="end">${esc(NF.format(Math.round(min)))}</text>
    <polyline class="line" points="${pts.map((p, i) => `${x(i)},${y(p.y)}`).join(" ")}"/>${labels}</svg></div>`;
}

const POS_BUCKETS = [["pos_1", "1"], ["pos_2_3", "2–3"], ["pos_4_10", "4–10"], ["pos_11_20", "11–20"], ["pos_21_30", "21–30"],
  ["pos_31_40", "31–40"], ["pos_41_50", "41–50"], ["pos_51_60", "51–60"], ["pos_61_70", "61–70"], ["pos_71_80", "71–80"],
  ["pos_81_90", "81–90"], ["pos_91_100", "91–100"]];

// Columnas reutilizables
const C = {
  keyword: { key: "keyword", label: "Keyword" },
  volume: { key: "search_volume", label: "Volumen", num: true, fmt: num },
  cpc: { key: "cpc", label: "CPC", num: true, fmt: money },
  compLevel: { key: "competition_level", label: "Competencia" },
  kd: { key: "keyword_difficulty", label: "KD", num: true, fmt: num },
  intent: { key: "main_intent", label: "Intención" },
  trend: { key: "monthly_searches", label: "Tendencia", fmt: (v) => sparkline(v), csv: (v) => (Array.isArray(v) ? v.map((m) => `${m.year}-${m.month}:${m.search_volume ?? ""}`).join(" ") : "") },
};
const labsKeywordCols = [C.keyword, C.volume, C.cpc, C.compLevel, C.kd, C.intent, C.trend];

// ---------------------------------------------------------------------------
// Definición de herramientas
// ---------------------------------------------------------------------------

const lines = (s) => s.split(/[\n,]+/).map((x) => x.trim()).filter(Boolean);

const TOOLS = [
  // Keywords ---------------------------------------------------------------
  {
    id: "kw-volume", group: "Keywords", title: "Volumen de búsqueda",
    desc: "Volumen mensual, CPC y competencia de Google Ads. Hasta 100 keywords por consulta (configurable).",
    fields: [{ name: "keywords", label: "Keywords (una por línea)", type: "textarea", wide: true, parse: lines }],
    geo: true, call: (b) => api("POST", "/api/keywords/volume", b),
    render: (r) => table([C.keyword, C.volume, C.cpc,
      { key: "competition", label: "Competencia" }, { key: "competition_index", label: "Índice comp.", num: true, fmt: num },
      { key: "low_top_of_page_bid", label: "Puja baja", num: true, fmt: money }, { key: "high_top_of_page_bid", label: "Puja alta", num: true, fmt: money },
      C.trend], r.data),
  },
  {
    id: "kw-related", group: "Keywords", title: "Keywords relacionadas",
    desc: "Búsquedas relacionadas de Google con volumen, dificultad e intención.",
    fields: [{ name: "keyword", label: "Keyword semilla", wide: true },
      { name: "depth", label: "Profundidad (0–4)", type: "number", value: 1 },
      { name: "limit", label: "Resultados", type: "number", value: 100 }],
    geo: true, call: (b) => api("POST", "/api/keywords/related", b),
    render: (r) => seedBlock(r.data) + table([...labsKeywordCols, { key: "depth", label: "Nivel", num: true, fmt: num }], r.data.items),
  },
  {
    id: "kw-suggestions", group: "Keywords", title: "Sugerencias (long tail)",
    desc: "Keywords que contienen la semilla, ideales para long tail.",
    fields: [{ name: "keyword", label: "Keyword semilla", wide: true },
      { name: "limit", label: "Resultados", type: "number", value: 100 },
      { name: "exact_match", label: "Frase exacta", type: "checkbox" }],
    geo: true, call: (b) => api("POST", "/api/keywords/suggestions", b),
    render: (r) => seedBlock(r.data) + table(labsKeywordCols, r.data.items),
  },
  {
    id: "kw-difficulty", group: "Keywords", title: "Dificultad",
    desc: "Keyword Difficulty (0–100) de DataForSEO Labs.",
    fields: [{ name: "keywords", label: "Keywords (una por línea)", type: "textarea", wide: true, parse: lines }],
    geo: true, call: (b) => api("POST", "/api/keywords/difficulty", b),
    render: (r) => table([C.keyword, C.kd], r.data),
  },
  {
    id: "kw-intent", group: "Keywords", title: "Intención de búsqueda",
    desc: "Clasificación informacional, navegacional, comercial o transaccional.",
    fields: [{ name: "keywords", label: "Keywords (una por línea)", type: "textarea", wide: true, parse: lines }],
    call: (b) => api("POST", "/api/keywords/intent", b),
    render: (r) => table([C.keyword, { key: "intent", label: "Intención" }, { key: "probability", label: "Probabilidad", num: true, fmt: pct },
      { key: "secondary", label: "Secundarias", fmt: (v) => (Array.isArray(v) ? v.map((s) => `<span class="chip">${esc(s.intent)} ${pct(s.probability)}</span>`).join("") : ""),
        csv: (v) => (Array.isArray(v) ? v.map((s) => `${s.intent}:${s.probability}`).join(" ") : "") }], r.data),
  },

  // Dominio ----------------------------------------------------------------
  {
    id: "dom-overview", group: "Dominio", title: "Visión general",
    desc: "Tráfico orgánico estimado, keywords posicionadas y distribución de posiciones.",
    fields: [{ name: "target", label: "Dominio", wide: true, placeholder: "ejemplo.com" }],
    geo: true, call: (b) => api("POST", "/api/domains/overview", b),
    render: (r) => {
      const o = r.data.organic || {}, p = r.data.paid || {};
      return cards([
        { label: "Tráfico orgánico estimado (ETV)", value: num(o.etv && Math.round(o.etv)) },
        { label: "Keywords orgánicas", value: num(o.count) },
        { label: "Valor del tráfico orgánico", value: money(o.estimated_paid_traffic_cost) },
        { label: "Keywords de pago", value: num(p.count) },
        { label: "Nuevas", value: num(o.is_new), cls: "good" },
        { label: "Suben", value: num(o.is_up), cls: "good" },
        { label: "Bajan", value: num(o.is_down), cls: "warn" },
        { label: "Perdidas", value: num(o.is_lost), cls: "bad" },
      ]) + (r.data.organic ? `<h2>Distribución de posiciones orgánicas</h2>${bars(POS_BUCKETS.map(([k, l]) => ({ label: l, value: o[k] })))}` : "<p class='muted'>La API no devolvió métricas orgánicas para este dominio.</p>");
    },
  },
  {
    id: "dom-ranked", group: "Dominio", title: "Keywords posicionadas",
    desc: "Keywords por las que posiciona el dominio, ordenadas por volumen.",
    fields: [{ name: "target", label: "Dominio o URL", wide: true },
      { name: "limit", label: "Resultados", type: "number", value: 100 },
      { name: "offset", label: "Desde", type: "number", value: 0 }],
    geo: true, call: (b) => api("POST", "/api/domains/ranked-keywords", b),
    render: (r) => `<p class="muted">Total en la base de datos: ${num(r.data.total_count)}</p>` + table([
      C.keyword, { key: "position.rank_group", label: "Pos.", num: true, fmt: num }, { key: "position.type", label: "Tipo" },
      { key: "position.url", label: "URL", cls: "url", fmt: link }, C.volume, { key: "position.etv", label: "Tráfico est.", num: true, fmt: dec },
      C.cpc, C.kd, C.intent], r.data.items),
  },
  {
    id: "dom-competitors", group: "Dominio", title: "Competidores",
    desc: "Dominios que compiten por las mismas keywords (excluye los gigantes como Wikipedia).",
    fields: [{ name: "target", label: "Dominio", wide: true }, { name: "limit", label: "Resultados", type: "number", value: 50 }],
    geo: true, call: (b) => api("POST", "/api/domains/competitors", b),
    render: (r) => table([{ key: "domain", label: "Dominio" }, { key: "intersections", label: "Keywords comunes", num: true, fmt: num },
      { key: "avg_position", label: "Pos. media", num: true, fmt: dec }, { key: "intersection_organic.etv", label: "ETV en comunes", num: true, fmt: dec },
      { key: "full_organic.count", label: "Keywords totales", num: true, fmt: num }, { key: "full_organic.etv", label: "ETV total", num: true, fmt: dec }], r.data.items),
  },
  {
    id: "dom-gap", group: "Dominio", title: "Keyword gap",
    desc: "Comunes: keywords en las que posicionan ambos. No comunes: keywords del dominio 1 que no tiene el dominio 2.",
    fields: [{ name: "target_1", label: "Dominio 1" }, { name: "target_2", label: "Dominio 2" },
      { name: "intersections", label: "Solo comunes", type: "checkbox", value: true },
      { name: "limit", label: "Resultados", type: "number", value: 100 }],
    geo: true, call: (b) => api("POST", "/api/domains/keyword-gap", b),
    render: (r) => table([C.keyword, C.volume, C.kd, C.intent,
      { key: "target_1.rank_group", label: "Pos. dominio 1", num: true, fmt: num }, { key: "target_2.rank_group", label: "Pos. dominio 2", num: true, fmt: num },
      { key: "target_1.url", label: "URL dominio 1", cls: "url", fmt: link }, { key: "target_2.url", label: "URL dominio 2", cls: "url", fmt: link }], r.data.items),
  },
  {
    id: "dom-pages", group: "Dominio", title: "Páginas principales",
    desc: "URLs con más tráfico orgánico estimado.",
    fields: [{ name: "target", label: "Dominio", wide: true }, { name: "limit", label: "Resultados", type: "number", value: 100 }],
    geo: true, call: (b) => api("POST", "/api/domains/top-pages", b),
    render: (r) => table([{ key: "page", label: "URL", cls: "url", fmt: link }, { key: "organic.etv", label: "Tráfico est.", num: true, fmt: dec },
      { key: "organic.count", label: "Keywords", num: true, fmt: num }, { key: "organic.pos_1", label: "Top 1", num: true, fmt: num },
      { key: "organic.pos_2_3", label: "Top 2–3", num: true, fmt: num }, { key: "organic.pos_4_10", label: "Top 4–10", num: true, fmt: num }], r.data.items),
  },
  {
    id: "dom-history", group: "Dominio", title: "Evolución histórica",
    desc: "Tráfico orgánico estimado y número de keywords mes a mes.",
    fields: [{ name: "target", label: "Dominio", wide: true }],
    geo: true, call: (b) => api("POST", "/api/domains/history", b),
    render: (r) => {
      const rows = [...r.data].sort((a, b) => a.year - b.year || a.month - b.month);
      const pt = (k) => rows.map((x) => ({ x: `${String(x.month).padStart(2, "0")}/${String(x.year).slice(2)}`, y: get(x, k) }));
      return lineChart(pt("organic.etv"), "Tráfico orgánico estimado") + lineChart(pt("organic.count"), "Keywords orgánicas") +
        table([{ key: "year", label: "Año" }, { key: "month", label: "Mes" }, { key: "organic.etv", label: "ETV orgánico", num: true, fmt: dec },
          { key: "organic.count", label: "Keywords", num: true, fmt: num }, { key: "organic.pos_1", label: "Top 1", num: true, fmt: num },
          { key: "organic.pos_4_10", label: "Top 4–10", num: true, fmt: num }, { key: "paid.count", label: "Keywords pago", num: true, fmt: num }], rows);
    },
  },
  {
    id: "dom-traffic", group: "Dominio", title: "Tráfico de varios dominios",
    desc: "Compara el tráfico estimado de una lista de dominios.",
    fields: [{ name: "targets", label: "Dominios (uno por línea)", type: "textarea", wide: true, parse: lines }],
    geo: true, call: (b) => api("POST", "/api/domains/traffic", b),
    render: (r) => table([{ key: "target", label: "Dominio" }, { key: "organic_etv", label: "ETV orgánico", num: true, fmt: dec },
      { key: "organic_keywords", label: "Keywords orgánicas", num: true, fmt: num }, { key: "paid_etv", label: "ETV pago", num: true, fmt: dec },
      { key: "paid_keywords", label: "Keywords pago", num: true, fmt: num }, { key: "featured_snippet_etv", label: "ETV fragmentos", num: true, fmt: dec },
      { key: "local_pack_etv", label: "ETV local pack", num: true, fmt: dec }], r.data),
  },

  // Backlinks --------------------------------------------------------------
  {
    id: "bl-summary", group: "Backlinks", title: "Resumen de enlaces",
    desc: "Perfil de enlaces: backlinks, dominios de referencia, spam score y distribución.",
    fields: [{ name: "target", label: "Dominio", wide: true }],
    call: (b) => api("POST", "/api/backlinks/summary", b),
    render: (r) => {
      const d = r.data;
      const dict = (o, l) => (o && typeof o === "object" ? table([{ key: "k", label: l }, { key: "v", label: "Enlaces", num: true, fmt: num }],
        Object.entries(o).map(([k, v]) => ({ k, v })).sort((a, b) => (b.v ?? 0) - (a.v ?? 0)), l) : "");
      return cards([
        { label: "Rank", value: num(d.rank) }, { label: "Backlinks", value: num(d.backlinks) },
        { label: "Dominios de referencia", value: num(d.referring_domains) }, { label: "Dominios nofollow", value: num(d.referring_domains_nofollow) },
        { label: "IPs de referencia", value: num(d.referring_ips) }, { label: "Subredes", value: num(d.referring_subnets) },
        { label: "Spam score", value: num(d.backlinks_spam_score) }, { label: "Backlinks rotos", value: num(d.broken_backlinks), cls: "bad" },
        { label: "Páginas rotas enlazadas", value: num(d.broken_pages), cls: "bad" }, { label: "Primer registro", value: esc(d.first_seen ?? "") },
      ]) + `<h2>Atributos</h2>${dict(d.referring_links_attributes, "Atributo")}<h2>Países</h2>${dict(d.referring_links_countries, "País")}<h2>TLD</h2>${dict(d.referring_links_tld, "TLD")}`;
    },
  },
  {
    id: "bl-list", group: "Backlinks", title: "Listado de backlinks",
    desc: "Enlaces entrantes ordenados por autoridad.",
    fields: [{ name: "target", label: "Dominio", wide: true }, { name: "limit", label: "Resultados", type: "number", value: 100 },
      { name: "mode", label: "Agrupar", type: "select", options: [["one_per_domain", "Uno por dominio"], ["as_is", "Todos"], ["one_per_anchor", "Uno por ancla"]] }],
    call: (b) => api("POST", "/api/backlinks/list", b),
    render: (r) => `<p class="muted">Total: ${num(r.data.total_count)}</p>` + table([
      { key: "url_from", label: "Desde", cls: "url", fmt: link }, { key: "url_to", label: "Hacia", cls: "url", fmt: link },
      { key: "anchor", label: "Ancla" }, { key: "dofollow", label: "Dofollow", fmt: yesno }, { key: "domain_from_rank", label: "Rank dominio", num: true, fmt: num },
      { key: "backlink_spam_score", label: "Spam", num: true, fmt: num }, { key: "first_seen", label: "Visto por primera vez" },
      { key: "is_lost", label: "Perdido", fmt: yesno }, { key: "is_broken", label: "Roto", fmt: yesno }], r.data.items),
  },
  {
    id: "bl-domains", group: "Backlinks", title: "Dominios de referencia",
    desc: "Dominios que enlazan al sitio.",
    fields: [{ name: "target", label: "Dominio", wide: true }, { name: "limit", label: "Resultados", type: "number", value: 100 }],
    call: (b) => api("POST", "/api/backlinks/referring-domains", b),
    render: (r) => `<p class="muted">Total: ${num(r.data.total_count)}</p>` + table([{ key: "domain", label: "Dominio" },
      { key: "rank", label: "Rank", num: true, fmt: num }, { key: "backlinks", label: "Backlinks", num: true, fmt: num },
      { key: "backlinks_spam_score", label: "Spam", num: true, fmt: num }, { key: "first_seen", label: "Primer registro" },
      { key: "lost_date", label: "Perdido" }], r.data.items),
  },
  {
    id: "bl-anchors", group: "Backlinks", title: "Textos ancla",
    desc: "Distribución de anclas de los enlaces entrantes.",
    fields: [{ name: "target", label: "Dominio", wide: true }, { name: "limit", label: "Resultados", type: "number", value: 100 }],
    call: (b) => api("POST", "/api/backlinks/anchors", b),
    render: (r) => table([{ key: "anchor", label: "Ancla" }, { key: "backlinks", label: "Backlinks", num: true, fmt: num },
      { key: "referring_domains", label: "Dominios", num: true, fmt: num }, { key: "rank", label: "Rank", num: true, fmt: num },
      { key: "backlinks_spam_score", label: "Spam", num: true, fmt: num }, { key: "first_seen", label: "Primer registro" }], r.data.items),
  },

  // SERP -------------------------------------------------------------------
  {
    id: "serp-organic", group: "SERP", title: "Resultados de Google",
    desc: "SERP orgánica en tiempo real. Se factura por cada bloque de 10 resultados.",
    fields: [{ name: "keyword", label: "Keyword", wide: true }, { name: "depth", label: "Resultados", type: "number", value: 10 },
      { name: "device", label: "Dispositivo", type: "select", options: [["desktop", "Escritorio"], ["mobile", "Móvil"]] }],
    geo: true, call: (b) => api("POST", "/api/serp/organic", b),
    render: (r) => serpFeatures(r.data) + table([{ key: "rank_group", label: "Pos.", num: true, fmt: num }, { key: "domain", label: "Dominio" },
      { key: "title", label: "Título" }, { key: "url", label: "URL", cls: "url", fmt: link }, { key: "description", label: "Descripción" }], r.data.organic),
  },
  {
    id: "serp-rank", group: "SERP", title: "Comprobar posición",
    desc: "¿En qué posición aparece un dominio para una keyword?",
    fields: [{ name: "keyword", label: "Keyword", wide: true }, { name: "domain", label: "Dominio" },
      { name: "depth", label: "Revisar hasta", type: "number", value: 100 },
      { name: "device", label: "Dispositivo", type: "select", options: [["desktop", "Escritorio"], ["mobile", "Móvil"]] }],
    geo: true, call: (b) => api("POST", "/api/serp/rank-check", b),
    render: (r) => cards([
      { label: "¿Aparece?", value: r.data.found ? "Sí" : "No", cls: r.data.found ? "good" : "bad" },
      { label: "Mejor posición", value: num(r.data.best_position) },
      { label: "Resultados revisados", value: num(r.data.checked_results) },
    ]) + table([{ key: "rank_group", label: "Pos.", num: true, fmt: num }, { key: "url", label: "URL", cls: "url", fmt: link }, { key: "title", label: "Título" }], r.data.matches),
  },

  // Auditoría --------------------------------------------------------------
  {
    id: "audit-crawl", group: "Auditoría técnica", title: "Rastreo del sitio",
    desc: "Rastreo completo tipo Screaming Frog con la On-Page API. Se factura por página rastreada; JavaScript, recursos y renderizado tienen coste adicional.",
    fields: [{ name: "target", label: "Dominio", wide: true }, { name: "max_crawl_pages", label: "Máx. páginas", type: "number", value: 100 },
      { name: "max_crawl_depth", label: "Profundidad máx.", type: "number" },
      { name: "enable_javascript", label: "Ejecutar JavaScript", type: "checkbox" },
      { name: "load_resources", label: "Cargar recursos (imágenes, CSS, JS)", type: "checkbox" },
      { name: "enable_browser_rendering", label: "Core Web Vitals (renderizado)", type: "checkbox" },
      { name: "respect_sitemap", label: "Seguir el sitemap", type: "checkbox" },
      { name: "check_spell", label: "Ortografía", type: "checkbox" }],
    submitLabel: "Lanzar rastreo",
    call: (b) => api("POST", "/api/audit/crawls", b),
    render: (r) => { setTimeout(() => openCrawl(r.data.task_id), 0); return metaLine(r.meta); },
    after: () => renderCrawlList(),
    onOpen: () => renderCrawlList(),
  },
  {
    id: "audit-page", group: "Auditoría técnica", title: "Análisis de una URL",
    desc: "Auditoría on-page instantánea de una sola página.",
    fields: [{ name: "url", label: "URL", wide: true, placeholder: "https://ejemplo.com/pagina" },
      { name: "enable_javascript", label: "Ejecutar JavaScript", type: "checkbox" }],
    call: (b) => api("POST", "/api/audit/page", b),
    render: (r) => (r.data ? pageDetail(r.data) : "<p class='muted'>La API no devolvió datos de la página.</p>"),
  },
  {
    id: "audit-lighthouse", group: "Auditoría técnica", title: "Lighthouse / velocidad",
    desc: "Puntuaciones de Lighthouse y métricas de rendimiento.",
    fields: [{ name: "url", label: "URL", wide: true }, { name: "for_mobile", label: "Móvil", type: "checkbox", value: true }],
    call: (b) => api("POST", "/api/audit/lighthouse", b),
    render: (r) => lighthouseView(r.data),
  },

  // Cuenta -----------------------------------------------------------------
  {
    id: "costs", group: "Cuenta", title: "Costes y caché",
    desc: "Gasto real registrado en cada llamada y ahorro gracias a la caché.",
    fields: [], submitLabel: "Actualizar",
    call: () => api("GET", "/api/costs"), auto: true,
    render: (d) => cards([
      { label: "Gasto total", value: money(d.total_cost) }, { label: "Gasto hoy (UTC)", value: money(d.spent_today_utc) },
      { label: "Llamadas a la API", value: num(d.total_calls) }, { label: "Aciertos de caché", value: num(d.cache_hits) },
      { label: "Ahorrado por caché", value: money(d.saved_by_cache), cls: "good" },
    ]) + `<p><button type="button" class="small secondary" id="btn-balance">Consultar saldo de DataForSEO</button>
      <button type="button" class="small secondary" id="btn-clear-cache">Vaciar caché</button> <span id="balance"></span></p>
      <h2>Por endpoint</h2>${table([{ key: "endpoint", label: "Endpoint" }, { key: "calls", label: "Llamadas", num: true, fmt: num },
        { key: "errors", label: "Errores", num: true, fmt: num }, { key: "cost", label: "Coste", num: true, fmt: money }], d.by_endpoint)}
      <h2>Por día</h2>${table([{ key: "day", label: "Día" }, { key: "calls", label: "Llamadas", num: true, fmt: num }, { key: "cost", label: "Coste", num: true, fmt: money }], d.by_day)}
      <h2>Últimas llamadas</h2>${table([{ key: "ts", label: "Fecha", fmt: (v) => esc(new Date(v * 1000).toLocaleString("es-ES")) },
        { key: "endpoint", label: "Endpoint" }, { key: "from_cache", label: "Caché", fmt: (v) => (v ? "Sí" : "") },
        { key: "cost", label: "Coste", num: true, fmt: money }, { key: "ok", label: "OK", fmt: (v) => (v ? "Sí" : "No") }, { key: "message", label: "Mensaje" }], d.recent)}`,
  },
];

function seedBlock(d) {
  const s = d.seed;
  const total = `<p class="muted">Total disponible: ${num(d.total_count)}</p>`;
  if (!s) return total;
  return cards([{ label: `Semilla: ${s.keyword ?? ""}`, value: num(s.search_volume) }, { label: "CPC", value: money(s.cpc) },
    { label: "Dificultad", value: num(s.keyword_difficulty) }, { label: "Intención", value: esc(s.main_intent ?? "") }]) + total;
}

function serpFeatures(d) {
  const f = Object.entries(d.features || {}).map(([k, v]) => `<span class="chip">${esc(k)} × ${v}</span>`).join("");
  return `<p class="muted">Resultados en Google: ${num(d.se_results_count)} ${d.check_url ? `· ${link(d.check_url)}` : ""}</p>` +
    (f ? `<p>Elementos de la SERP: ${f}</p>` : "");
}

function pageDetail(p) {
  const failed = (p.failed_checks || []).map((c) => `<span class="chip bad">${esc(c)}</span>`).join("") || "<span class='muted'>Ninguno</span>";
  const score = p.onpage_score;
  return cards([
    { label: "Puntuación on-page", value: dec(score), cls: isNum(score) ? (score >= 90 ? "good" : score >= 70 ? "warn" : "bad") : "" },
    { label: "Código HTTP", value: num(p.status_code) }, { label: "Palabras", value: num(p.words_count) },
    { label: "Enlaces internos", value: num(p.internal_links_count) }, { label: "Enlaces externos", value: num(p.external_links_count) },
    { label: "Imágenes", value: num(p.images_count) }, { label: "Tamaño (bytes)", value: num(p.size) },
    { label: "Tiempo de carga (ms)", value: num(p.duration_time) },
  ]) + table([{ key: "k", label: "Elemento" }, { key: "v", label: "Valor" }], [
    { k: "URL", v: p.url }, { k: "Title", v: p.title }, { k: "Longitud del title", v: p.title_length },
    { k: "Meta description", v: p.description }, { k: "Longitud de la description", v: p.description_length },
    { k: "H1", v: Array.isArray(p.h1) ? p.h1.join(" | ") : null }, { k: "Canonical", v: p.canonical },
  ]) + `<h2>Problemas detectados</h2><p>${failed}</p>`;
}

function lighthouseView(d) {
  if (!d) return "<p class='muted'>La API no devolvió resultados de Lighthouse.</p>";
  const names = { performance: "Rendimiento", accessibility: "Accesibilidad", "best-practices": "Buenas prácticas", seo: "SEO", pwa: "PWA" };
  const color = (s) => (s >= 90 ? "var(--good)" : s >= 50 ? "var(--warn)" : "var(--bad)");
  const gauges = Object.entries(d.scores || {}).map(([k, s]) => `<div class="gauge"><div class="ring" style="border:6px solid ${isNum(s) ? color(s) : "var(--border)"}">${isNum(s) ? s : ""}</div><div class="name">${esc(names[k] || k)}</div></div>`).join("");
  return `<p class="muted">${link(d.final_url || d.requested_url)} · Lighthouse ${esc(d.lighthouse_version ?? "")}</p><div class="gauges">${gauges}</div>
    <h2>Métricas</h2>${table([{ key: "title", label: "Métrica" }, { key: "display_value", label: "Valor" }, { key: "score", label: "Puntuación", num: true, fmt: dec }],
      Object.entries(d.metrics || {}).map(([id, v]) => ({ ...v, title: v.title || id })))}
    <h2>Oportunidades de mejora</h2>${table([{ key: "title", label: "Oportunidad" }, { key: "display_value", label: "Ahorro estimado" }, { key: "score", label: "Puntuación", num: true, fmt: dec }], d.opportunities)}`;
}

// ---------------------------------------------------------------------------
// Rastreos (vista de detalle con pestañas)
// ---------------------------------------------------------------------------

async function renderCrawlList() {
  if (currentTool?.id !== "audit-crawl") return;
  const res = await api("GET", "/api/audit/crawls");
  const holder = document.createElement("div");
  holder.id = "crawl-list";
  holder.innerHTML = `<h2>Rastreos lanzados</h2>` + table([
    { key: "target", label: "Dominio" }, { key: "max_crawl_pages", label: "Máx. páginas", num: true, fmt: num },
    { key: "created_at", label: "Fecha", fmt: (v) => esc(new Date(v * 1000).toLocaleString("es-ES")) },
    { key: "task_id", label: "", fmt: (v) => `<button type="button" class="small" data-open-crawl="${esc(v)}">Ver informe</button>` }], res.data);
  $("#crawl-list")?.remove();
  $("#output").prepend(holder);
}

document.addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-open-crawl]");
  if (b) openCrawl(b.dataset.openCrawl);
});

const CRAWL_TABS = [
  { id: "pages", label: "Páginas", path: "pages", cols: [
    { key: "url", label: "URL", cls: "url", fmt: link }, { key: "status_code", label: "HTTP", num: true, fmt: num },
    { key: "onpage_score", label: "Puntuación", num: true, fmt: dec }, { key: "click_depth", label: "Profundidad", num: true, fmt: num },
    { key: "title", label: "Title" }, { key: "title_length", label: "Long. title", num: true, fmt: num },
    { key: "description_length", label: "Long. desc.", num: true, fmt: num }, { key: "h1", label: "H1", fmt: (v) => esc(Array.isArray(v) ? v.join(" | ") : "") },
    { key: "words_count", label: "Palabras", num: true, fmt: num }, { key: "inbound_links_count", label: "Enlaces entrantes", num: true, fmt: num },
    { key: "duration_time", label: "Carga (ms)", num: true, fmt: num },
    { key: "failed_checks", label: "Problemas", fmt: (v) => (v || []).map((c) => `<span class="chip bad">${esc(c)}</span>`).join("") }] },
  { id: "broken-links", label: "Enlaces rotos", path: "broken-links", cols: [
    { key: "link_from", label: "Desde", cls: "url", fmt: link }, { key: "link_to", label: "Hacia", cls: "url", fmt: link },
    { key: "page_to_status_code", label: "HTTP", num: true, fmt: num }, { key: "direction", label: "Tipo" }, { key: "text", label: "Texto" }] },
  { id: "broken-resources", label: "Recursos con error", path: "broken-resources", cols: [
    { key: "url", label: "URL", cls: "url", fmt: link }, { key: "resource_type", label: "Tipo" }, { key: "status_code", label: "HTTP", num: true, fmt: num }] },
  { id: "dup-title", label: "Titles duplicados", path: "duplicates?type=duplicate_title", cols: [
    { key: "value", label: "Title" }, { key: "total_count", label: "Páginas", num: true, fmt: num },
    { key: "pages", label: "URLs", cls: "url", fmt: (v) => (v || []).map(link).join("<br>") }] },
  { id: "dup-desc", label: "Descriptions duplicadas", path: "duplicates?type=duplicate_description", cols: [
    { key: "value", label: "Description" }, { key: "total_count", label: "Páginas", num: true, fmt: num },
    { key: "pages", label: "URLs", cls: "url", fmt: (v) => (v || []).map(link).join("<br>") }] },
  { id: "redirects", label: "Redirecciones", path: "redirect-chains", cols: [
    { key: "is_redirect_loop", label: "Bucle", fmt: yesno },
    { key: "chain", label: "Cadena", cls: "url", fmt: (v) => (v || []).map((c) => `${esc(c.from)} → ${esc(c.to)} <span class="chip">${esc(c.status_code ?? "")}</span>`).join("<br>") }] },
  { id: "non-indexable", label: "No indexables", path: "non-indexable", cols: [
    { key: "url", label: "URL", cls: "url", fmt: link }, { key: "reason", label: "Motivo" }] },
];

async function openCrawl(taskId) {
  const out = $("#output");
  const box = document.createElement("div");
  box.id = "crawl-detail";
  box.innerHTML = `<p class="muted">Cargando resumen del rastreo…</p>`;
  $("#crawl-detail")?.remove();
  out.append(box);
  box.scrollIntoView({ behavior: "smooth", block: "start" });
  try {
    const r = await api("GET", `/api/audit/crawls/${encodeURIComponent(taskId)}/summary`);
    const s = r.data, pm = s.page_metrics || {}, cs = s.crawl_status || {}, di = s.domain_info || {};
    const finished = s.crawl_progress === "finished";
    box.innerHTML = `<h2>Informe de ${esc(di.name ?? taskId)}</h2>` + metaLine(r.meta, `<span class="tag">Estado: ${esc(s.crawl_progress ?? "")}</span>`) +
      `<p><button type="button" class="small secondary" data-open-crawl="${esc(taskId)}">Actualizar</button>
        ${finished ? "" : "<span class='muted'>El rastreo sigue en curso: actualiza en unos minutos.</span>"}</p>` +
      cards([
        { label: "Puntuación on-page", value: dec(pm.onpage_score) },
        { label: "Páginas rastreadas", value: `${num(cs.pages_crawled)} / ${num(cs.max_crawl_pages)}` },
        { label: "En cola", value: num(cs.pages_in_queue) },
        { label: "Enlaces rotos", value: num(pm.broken_links), cls: pm.broken_links ? "bad" : "" },
        { label: "Recursos rotos", value: num(pm.broken_resources), cls: pm.broken_resources ? "bad" : "" },
        { label: "Titles duplicados", value: num(pm.duplicate_title), cls: pm.duplicate_title ? "warn" : "" },
        { label: "Descriptions duplicadas", value: num(pm.duplicate_description), cls: pm.duplicate_description ? "warn" : "" },
        { label: "Contenido duplicado", value: num(pm.duplicate_content), cls: pm.duplicate_content ? "warn" : "" },
        { label: "Bucles de redirección", value: num(pm.redirect_loop), cls: pm.redirect_loop ? "bad" : "" },
        { label: "No indexables", value: num(pm.non_indexable) },
        { label: "Enlaces internos", value: num(pm.links_internal) },
        { label: "Enlaces externos", value: num(pm.links_external) },
      ]) +
      `<h2>Problemas por número de páginas</h2>` + table([
        { key: "label", label: "Problema", fmt: (v, row) => esc(v || row.check) },
        { key: "check", label: "Clave DataForSEO", fmt: (v) => `<code>${esc(v)}</code>` },
        { key: "informational", label: "Tipo", fmt: (v) => (v ? "Informativa" : "Problema") },
        { key: "value", label: "Páginas", num: true, fmt: num }], s.issues) +
      `<h2>Comprobaciones del sitio</h2>` + table([
        { key: "label", label: "Comprobación", fmt: (v, row) => esc(v || row.check) },
        { key: "check", label: "Clave", fmt: (v) => `<code>${esc(v)}</code>` }, { key: "value", label: "Resultado", fmt: yesno }], s.site_checks) +
      `<h2>Detalle</h2><div class="tabs">${CRAWL_TABS.map((t) => `<button type="button" data-crawl-tab="${t.id}" data-task="${esc(taskId)}">${esc(t.label)}</button>`).join("")}</div><div id="crawl-tab"></div>`;
  } catch (e) {
    box.innerHTML = `<div class="status error">${esc(e.message)}</div>`;
  }
}

document.addEventListener("click", async (ev) => {
  const b = ev.target.closest("[data-crawl-tab]");
  if (!b) return;
  const tab = CRAWL_TABS.find((t) => t.id === b.dataset.crawlTab);
  document.querySelectorAll("[data-crawl-tab]").forEach((x) => x.classList.toggle("active", x === b));
  const holder = $("#crawl-tab");
  holder.innerHTML = `<p class="muted">Cargando…</p>`;
  try {
    const sep = tab.path.includes("?") ? "&" : "?";
    const r = await api("GET", `/api/audit/crawls/${encodeURIComponent(b.dataset.task)}/${tab.path}${sep}limit=1000`);
    holder.innerHTML = metaLine(r.meta, `<span>Total: ${num(r.data.total_count)}</span>`) + table(tab.cols, r.data.items, tab.label);
  } catch (e) {
    holder.innerHTML = `<div class="status error">${esc(e.message)}</div>`;
  }
});

// ---------------------------------------------------------------------------
// Navegación y formularios
// ---------------------------------------------------------------------------

let currentTool = null;

function buildNav() {
  const nav = $("#nav");
  let group = "";
  for (const t of TOOLS) {
    if (t.group !== group) {
      group = t.group;
      nav.insertAdjacentHTML("beforeend", `<div class="group">${esc(group)}</div>`);
    }
    nav.insertAdjacentHTML("beforeend", `<button type="button" data-tool="${t.id}">${esc(t.title)}</button>`);
  }
  nav.addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-tool]");
    if (b) openTool(b.dataset.tool);
  });
}

function fieldHtml(f) {
  const id = `f-${f.name}`;
  if (f.type === "checkbox") {
    return `<div class="field check"><input type="checkbox" id="${id}" name="${f.name}" ${f.value ? "checked" : ""}><label for="${id}">${esc(f.label)}</label></div>`;
  }
  let input;
  if (f.type === "textarea") input = `<textarea id="${id}" name="${f.name}" placeholder="${esc(f.placeholder || "")}"></textarea>`;
  else if (f.type === "select") input = `<select id="${id}" name="${f.name}">${f.options.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("")}</select>`;
  else input = `<input id="${id}" name="${f.name}" type="${f.type || "text"}" value="${f.value ?? ""}" placeholder="${esc(f.placeholder || "")}">`;
  return `<div class="field ${f.wide ? "wide" : ""}"><label for="${id}">${esc(f.label)}</label>${input}</div>`;
}

function openTool(id) {
  const tool = TOOLS.find((t) => t.id === id) || TOOLS[0];
  currentTool = tool;
  tables.clear();
  try { localStorage.setItem("sniplyze.tool", tool.id); } catch { /* sin almacenamiento */ }
  document.querySelectorAll("#nav [data-tool]").forEach((b) => b.classList.toggle("active", b.dataset.tool === tool.id));
  $("#tool-title").textContent = tool.title;
  $("#tool-desc").textContent = tool.desc;
  const form = $("#tool-form");
  form.innerHTML = tool.fields.map(fieldHtml).join("") +
    `<div class="field"><button class="primary" type="submit">${esc(tool.submitLabel || "Consultar")}</button></div>`;
  $("#output").innerHTML = "";
  setStatus("");
  if (tool.auto) form.requestSubmit();
  tool.onOpen?.();
}

function readForm(tool) {
  const form = $("#tool-form");
  const body = {};
  for (const f of tool.fields) {
    const el = form.elements[f.name];
    if (f.type === "checkbox") body[f.name] = el.checked;
    else if (f.type === "number") { const v = el.value.trim(); body[f.name] = v === "" ? null : Number(v); }
    else body[f.name] = f.parse ? f.parse(el.value) : el.value.trim();
  }
  if (tool.geo) Object.assign(body, geo());
  return body;
}

function setStatus(msg, isError = false) {
  const el = $("#status");
  el.hidden = !msg;
  el.className = `status ${isError ? "error" : ""}`;
  el.textContent = msg;
}

$("#tool-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const tool = currentTool;
  const btn = ev.target.querySelector("button[type=submit]");
  btn.disabled = true;
  setStatus("Consultando…");
  try {
    const res = await tool.call(readForm(tool));
    if (tool !== currentTool) return;
    tables.clear();
    $("#output").innerHTML = (res?.meta && tool.id !== "audit-crawl" ? metaLine(res.meta) : "") + tool.render(res);
    setStatus("");
    tool.after?.();
    bindCostButtons();
  } catch (e) {
    setStatus(e.message, true);
  } finally {
    btn.disabled = false;
  }
});

function bindCostButtons() {
  $("#btn-balance")?.addEventListener("click", async () => {
    try {
      const r = await api("GET", "/api/account");
      $("#balance").textContent = `Saldo: ${money(r.data.balance)}`;
    } catch (e) { $("#balance").textContent = e.message; }
  });
  $("#btn-clear-cache")?.addEventListener("click", async () => {
    const r = await api("DELETE", "/api/cache");
    $("#balance").textContent = `Caché vaciada (${num(r.deleted)} entradas).`;
  });
}

async function init() {
  buildNav();
  try {
    const cfg = await api("GET", "/api/config");
    $("#geo-location").value = cfg.default_location_code;
    $("#geo-language").value = cfg.default_language_code;
    if (!cfg.credentials_configured) {
      const b = $("#banner");
      b.hidden = false;
      b.textContent = "Faltan las credenciales de DataForSEO: copia .env.example a .env, rellena DATAFORSEO_LOGIN y DATAFORSEO_PASSWORD y reinicia.";
    }
  } catch (e) {
    setStatus(e.message, true);
  }
  let last = null;
  try { last = localStorage.getItem("sniplyze.tool"); } catch { /* sin almacenamiento */ }
  openTool(last || TOOLS[0].id);
}

init();
