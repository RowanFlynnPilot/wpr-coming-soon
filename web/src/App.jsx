// Coming Soon tracker widget — Wausau Pilot & Review.
// Consumes exactly one file: locations.json (deployed next to the build).
// Branding follows the paper's widget design system (see app.css).

import React, { useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { CONFIG } from './config.js'

const KIND_LABELS = {
  sign_permit: 'Sign permit',
  new_commercial_construction: 'Construction permit',
  commercial_alteration: 'Building permit',
  commercial_sale: 'Property sale',
  alcohol_license_application: 'License application',
}

function fmtDate(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}

// The receipt reference shown after the kind + date, per source.
function receiptRef(signal) {
  const r = signal.receipt
  if (signal.source === 'permit') return `#${r.permit_number}`
  if (signal.source === 'transfer') return `doc #${r.document_number}`
  if (signal.source === 'license') return r.body
  return null
}

function Masthead() {
  return (
    <header className="masthead">
      <div className="masthead__title">
        <a href="https://wausaupilotandreview.com" target="_top">
          <img
            className="masthead__badge"
            src={CONFIG.WPR_BADGE}
            alt=""
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />
          Wausau Pilot &amp; Review
        </a>
      </div>
      <div className="masthead__tag">Independent. Local. Nonprofit news.</div>
    </header>
  )
}

// One renderer for the sponsor slot ({ text, href, logo }), house pattern.
function Sponsor({ slot, className }) {
  if (!slot || !slot.text) return null
  const inner = (
    <>
      {slot.logo && <img src={slot.logo} alt="" loading="lazy" />}
      <span>{slot.text}</span>
    </>
  )
  if (slot.href) {
    return (
      <a className={className} href={slot.href} target="_blank" rel="noopener sponsored">
        {inner}
      </a>
    )
  }
  return <span className={className}>{inner}</span>
}

function Receipt({ signal }) {
  const line = [KIND_LABELS[signal.kind] || signal.kind, fmtDate(signal.observed), receiptRef(signal)]
    .filter(Boolean)
    .join(' · ')
  return (
    <li>
      {signal.url ? (
        <a href={signal.url} target="_blank" rel="noreferrer">
          {line}
        </a>
      ) : (
        line
      )}
      <span className="receipts__summary"> — {signal.summary}</span>
    </li>
  )
}

function Card({ loc }) {
  const open = loc.status === 'open'
  return (
    <article className={open ? 'card card--open' : 'card'}>
      <div className="card__head">
        <h2 className="card__name">{loc.name}</h2>
        <span className={open ? 'status status--open' : 'status'}>
          {open ? 'Now open' : 'Coming soon'}
        </span>
      </div>
      <div className="card__meta">
        {loc.category && <span className="chip">{loc.category}</span>}
        <span className="card__addr">
          {loc.address}, {loc.municipality}
        </span>
        {open && loc.opened && <span className="card__opened">opened {fmtDate(loc.opened)}</span>}
      </div>
      {loc.note && <p className="card__note">{loc.note}</p>}
      <div className="receipts">
        <div className="receipts__label">The receipts</div>
        <ul>
          {loc.signals
            .slice()
            .reverse()
            .map((s) => (
              <Receipt key={s.id} signal={s} />
            ))}
        </ul>
      </div>
    </article>
  )
}

// Locations gain lat/lon at deploy time (scripts/enrich_geo.py) from the
// permit tracker's geocodes — the pipeline itself never geocodes.
function MapView({ locations }) {
  const ref = useRef(null)
  const pts = locations.filter((l) => l.lat != null && l.lon != null)

  useEffect(() => {
    if (!ref.current || pts.length === 0) return undefined
    const map = L.map(ref.current, { scrollWheelZoom: false })
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map)
    pts.forEach((l) => {
      const open = l.status === 'open'
      L.circleMarker([l.lat, l.lon], {
        radius: 9,
        color: open ? '#2e7d46' : '#3a867c',
        fillColor: open ? '#2e7d46' : '#3a867c',
        fillOpacity: 0.85,
        weight: 2,
      })
        .addTo(map)
        .bindPopup(
          `<strong>${l.name}</strong><br>${l.address}, ${l.municipality}<br>` +
            (open ? 'Now open' : 'Coming soon')
        )
    })
    map.fitBounds(L.latLngBounds(pts.map((l) => [l.lat, l.lon])).pad(0.25), {
      maxZoom: 15,
    })
    return () => map.remove()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(pts.map((l) => l.key))])

  if (pts.length === 0) {
    return <p className="notice">None of the current entries carry map coordinates yet.</p>
  }
  return (
    <>
      <div ref={ref} className="map" />
      <p className="map__note">
        {pts.length} of {locations.length} shown — entries pin only once a geocoded permit
        backs them.
      </p>
    </>
  )
}

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [muni, setMuni] = useState('')
  const [category, setCategory] = useState('')
  const [view, setView] = useState('list')

  useEffect(() => {
    fetch('./locations.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData, setError)
  }, [])

  const locations = data ? data.locations : []
  const munis = useMemo(() => [...new Set(locations.map((l) => l.municipality))].sort(), [locations])
  const categories = useMemo(
    () => [...new Set(locations.map((l) => l.category).filter(Boolean))].sort(),
    [locations]
  )
  const shown = locations.filter(
    (l) => (!muni || l.municipality === muni) && (!category || l.category === category)
  )

  return (
    <div className="wrap">
      <Masthead />

      <div className="banner">
        <div>
          <div className="banner__kicker">Wausau area · new business tracker</div>
          <h1 className="banner__title">Coming Soon</h1>
        </div>
        <Sponsor slot={CONFIG.TITLE_SPONSOR} className="banner__sponsor" />
      </div>

      <div className="topbar">
        <span>What&rsquo;s going in that building? Every entry backed by public records.</span>
        {data && <span className="updated">updated {fmtDate(data.generated.slice(0, 10))}</span>}
      </div>

      {locations.length > 0 && (
        <div className="filters">
          <div className="viewtoggle" role="tablist">
            {['list', 'map'].map((v) => (
              <button
                key={v}
                role="tab"
                aria-selected={view === v}
                onClick={() => setView(v)}
              >
                {v === 'list' ? 'List' : 'Map'}
              </button>
            ))}
          </div>
          <label>
            Town
            <select value={muni} onChange={(e) => setMuni(e.target.value)}>
              <option value="">All</option>
              {munis.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </label>
          <label>
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All</option>
              {categories.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {error && (
        <p className="notice notice--error">
          Couldn&rsquo;t load the tracker ({String(error.message || error)}).
        </p>
      )}
      {data && locations.length === 0 && (
        <p className="notice">
          Nothing confirmed just yet — permits, property sales, and license applications are
          accruing, and entries appear here once our editors verify what&rsquo;s moving in.
        </p>
      )}
      {view === 'map' && locations.length > 0 && <MapView locations={shown} />}
      {view === 'list' &&
        shown.map((loc) => (
          <Card key={loc.key} loc={loc} />
        ))}

      <footer className="footer">
        <img
          className="footer__badge"
          src={CONFIG.WPR_BADGE}
          alt=""
          onError={(e) => {
            e.currentTarget.style.display = 'none'
          }}
        />
        <div>
          <p>
            Built from municipal building permits, state deed-transfer returns, and city license
            agendas — every entry shows the public records behind it. Confirmed by Wausau Pilot
            &amp; Review editors before publication.
          </p>
          <p>
            <a className="footer__sponsorlink" href={`mailto:${CONFIG.SPONSOR_INQUIRY}`}>
              Sponsor this tracker
            </a>
          </p>
        </div>
      </footer>
    </div>
  )
}
