// Coming Soon tracker widget — Wausau Pilot & Review.
// Consumes exactly one file: locations.json (deployed next to the build).
// See docs/WIDGET.md; WPR design system per house convention (inline styles).

import React, { useEffect, useMemo, useState } from "react";

const TEAL = "#4aaba7";
const TEAL_DARK = "#3e847a";
const INK = "#1A1209";
const CREAM = "#F7F3EC";
const RULE = "#E0D8CC";
const GOLD = "#8B6914";

const DISPLAY = "'Bebas Neue', sans-serif";
const HEADLINE = "'Playfair Display', serif";
const BODY = "'Lora', serif";
const MONO = "Consolas, Menlo, monospace";

const KIND_LABELS = {
  sign_permit: "Sign permit",
  new_commercial_construction: "Construction permit",
  commercial_alteration: "Building permit",
  commercial_sale: "Property sale",
  alcohol_license_application: "License application",
};

function fmtDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

// The receipt reference shown after the kind + date, per source.
function receiptRef(signal) {
  const r = signal.receipt;
  if (signal.source === "permit") return `#${r.permit_number}`;
  if (signal.source === "transfer") return `doc #${r.document_number}`;
  if (signal.source === "license") return r.body;
  return null;
}

function Receipt({ signal }) {
  const line = [KIND_LABELS[signal.kind] || signal.kind, fmtDate(signal.observed), receiptRef(signal)]
    .filter(Boolean)
    .join(" · ");
  return (
    <li style={{ fontFamily: MONO, fontSize: 12, color: "#5a4f3f", margin: "3px 0" }}>
      {signal.url ? (
        <a href={signal.url} target="_blank" rel="noreferrer" style={{ textDecorationColor: RULE }}>
          {line}
        </a>
      ) : (
        line
      )}
      <span style={{ fontFamily: BODY, fontStyle: "italic" }}> — {signal.summary}</span>
    </li>
  );
}

function Badge({ status }) {
  const open = status === "open";
  return (
    <span
      style={{
        fontFamily: DISPLAY,
        fontSize: 14,
        letterSpacing: 1.5,
        color: "#fff",
        background: open ? GOLD : TEAL_DARK,
        padding: "3px 10px 1px",
        borderRadius: 3,
        whiteSpace: "nowrap",
      }}
    >
      {open ? "Now open" : "Coming soon"}
    </span>
  );
}

function Card({ loc }) {
  const open = loc.status === "open";
  return (
    <article
      style={{
        background: "#fff",
        border: `1px solid ${open ? GOLD : RULE}`,
        borderTop: `4px solid ${open ? GOLD : TEAL}`,
        borderRadius: 4,
        padding: "16px 18px",
        marginBottom: 14,
        boxShadow: open ? "0 2px 10px rgba(139,105,20,.15)" : "none",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "baseline" }}>
        <h2 style={{ fontFamily: HEADLINE, fontWeight: 800, fontSize: 22, color: INK }}>
          {loc.name}
        </h2>
        <Badge status={loc.status} />
      </div>

      <div style={{ display: "flex", gap: 10, alignItems: "center", margin: "6px 0 8px", flexWrap: "wrap" }}>
        {loc.category && (
          <span
            style={{
              fontFamily: DISPLAY,
              fontSize: 13,
              letterSpacing: 1,
              color: TEAL_DARK,
              border: `1px solid ${TEAL}`,
              padding: "2px 8px 0",
              borderRadius: 10,
            }}
          >
            {loc.category}
          </span>
        )}
        <span style={{ fontFamily: MONO, fontSize: 13, color: "#5a4f3f" }}>
          {loc.address}, {loc.municipality}
        </span>
        {open && loc.opened && (
          <span style={{ fontFamily: MONO, fontSize: 13, color: GOLD }}>
            opened {fmtDate(loc.opened)}
          </span>
        )}
      </div>

      {loc.note && (
        <p style={{ fontFamily: BODY, fontSize: 15, color: INK, margin: "8px 0 10px" }}>{loc.note}</p>
      )}

      <div style={{ borderTop: `1px solid ${RULE}`, paddingTop: 8 }}>
        <div style={{ fontFamily: DISPLAY, fontSize: 12, letterSpacing: 1.5, color: "#8a7c66" }}>
          The receipts
        </div>
        <ul style={{ listStyle: "none", marginTop: 4 }}>
          {loc.signals.slice().reverse().map((s) => (
            <Receipt key={s.id} signal={s} />
          ))}
        </ul>
      </div>
    </article>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <label style={{ fontFamily: DISPLAY, fontSize: 14, letterSpacing: 1, color: TEAL_DARK }}>
      {label}{" "}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          font: `13px ${MONO}`,
          border: `1px solid ${RULE}`,
          borderRadius: 3,
          padding: "3px 6px",
          background: "#fff",
          color: INK,
        }}
      >
        <option value="">All</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [muni, setMuni] = useState("");
  const [category, setCategory] = useState("");

  useEffect(() => {
    fetch("./locations.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData, setError);
  }, []);

  const locations = data ? data.locations : [];
  const munis = useMemo(() => [...new Set(locations.map((l) => l.municipality))].sort(), [locations]);
  const categories = useMemo(
    () => [...new Set(locations.map((l) => l.category).filter(Boolean))].sort(),
    [locations]
  );
  const shown = locations.filter(
    (l) => (!muni || l.municipality === muni) && (!category || l.category === category)
  );

  return (
    <div style={{ maxWidth: 680, margin: "0 auto", padding: "20px 14px 40px", background: CREAM }}>
      <header style={{ borderBottom: `3px solid ${INK}`, paddingBottom: 10, marginBottom: 4 }}>
        <h1 style={{ fontFamily: DISPLAY, fontSize: 44, letterSpacing: 2, color: INK, lineHeight: 1 }}>
          Coming <span style={{ color: TEAL }}>Soon</span>
        </h1>
        <p style={{ fontFamily: BODY, fontStyle: "italic", fontSize: 14, color: "#5a4f3f" }}>
          What&rsquo;s going in that building? Every entry backed by public records.
        </p>
      </header>

      {/* Title sponsor slot */}
      <div
        style={{
          fontFamily: DISPLAY,
          fontSize: 13,
          letterSpacing: 1.5,
          color: "#8a7c66",
          borderBottom: `1px solid ${RULE}`,
          padding: "6px 0",
          marginBottom: 14,
        }}
      >
        Presented by — <span style={{ color: TEAL_DARK }}>your business here</span>
      </div>

      {locations.length > 0 && (
        <div style={{ display: "flex", gap: 18, marginBottom: 16, flexWrap: "wrap" }}>
          <Select label="Town" value={muni} onChange={setMuni} options={munis} />
          <Select label="Category" value={category} onChange={setCategory} options={categories} />
        </div>
      )}

      {error && (
        <p style={{ fontFamily: BODY, color: "#8a2f1f" }}>
          Couldn&rsquo;t load the tracker ({String(error.message || error)}).
        </p>
      )}
      {data && locations.length === 0 && (
        <p style={{ fontFamily: BODY, fontSize: 15, color: INK }}>
          Nothing confirmed just yet — permits, property sales, and license
          applications are accruing, and entries appear here once our editors
          verify what&rsquo;s moving in.
        </p>
      )}
      {shown.map((loc) => (
        <Card key={loc.key} loc={loc} />
      ))}

      <footer
        style={{
          fontFamily: MONO,
          fontSize: 11,
          color: "#8a7c66",
          borderTop: `1px solid ${RULE}`,
          paddingTop: 8,
          marginTop: 10,
        }}
      >
        {data && <>Updated {fmtDate(data.generated.slice(0, 10))} · </>}
        Wausau Pilot &amp; Review — built from building permits, deed transfers,
        and license agendas.
      </footer>
    </div>
  );
}
