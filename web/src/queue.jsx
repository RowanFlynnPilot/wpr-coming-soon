// Editor queue — internal by convention, not secrecy (everything in
// queue.json is public record). Renders every signal-status location with
// its receipts and copy-ready override YAML for data/overrides/locations.yaml.

import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { KIND_LABELS, fmtDate, receiptRef } from './format.js'
import './app.css'

function confirmYaml(loc) {
  return [
    `  "${loc.key}":`,
    '    status: coming_soon',
    '    name: ""',
    '    category: ""   # freeform, keep it consistent: restaurant, bar, retail, service…',
    '    note: ""',
  ].join('\n')
}

function suppressYaml(loc) {
  return `  "${loc.key}":\n    suppress: true`
}

// One block per selected entry — the sign-permit refacing wall shouldn't
// take one copy-paste per address.
function bulkSuppressYaml(locs) {
  return locs.map(suppressYaml).join('\n')
}

function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      className="copybtn"
      onClick={() => {
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        })
      }}
    >
      {copied ? 'Copied' : label}
    </button>
  )
}

const NEW_DAYS = 7

function daysBetween(a, b) {
  return Math.round((new Date(b) - new Date(a)) / 86400000)
}

// Deterministic story-strength score for the "Strongest" sort: sources
// converging on one address matter most, a license item is the best single
// signal, and more receipts beat fewer.
function strength(loc) {
  const sources = new Set(loc.signals.map((s) => s.source)).size
  const license = loc.signals.some((s) => s.source === 'license') ? 5 : 0
  return sources * 10 + license + loc.signals.length
}

function Entry({ loc, isNew, selected, onToggle }) {
  return (
    <article className={isNew ? 'card qentry qentry--new' : 'card qentry'}>
      <div className="card__head">
        <label className="qentry__select">
          <input type="checkbox" checked={selected} onChange={onToggle} />
          <h2 className="card__name qentry__key">{loc.key}</h2>
        </label>
        <span className="qentry__badges">
          {isNew && <span className="status status--new">New</span>}
          <span className="status">
            {loc.signals.length} signal{loc.signals.length === 1 ? '' : 's'}
          </span>
        </span>
      </div>
      <div className="card__meta">
        <span className="card__addr">
          {loc.address}, {loc.municipality}
        </span>
        <span className="card__addr">
          first seen {fmtDate(loc.first_seen)}
          {loc.last_arrival && loc.last_arrival !== loc.first_seen &&
            ` · newest signal ${fmtDate(loc.last_arrival)}`}
        </span>
      </div>
      <div className="receipts">
        <ul>
          {loc.signals
            .slice()
            .reverse()
            .map((s) => (
              <li key={s.id}>
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {[KIND_LABELS[s.kind] || s.kind, fmtDate(s.observed), receiptRef(s)]
                      .filter(Boolean)
                      .join(' · ')}
                  </a>
                ) : (
                  [KIND_LABELS[s.kind] || s.kind, fmtDate(s.observed), receiptRef(s)]
                    .filter(Boolean)
                    .join(' · ')
                )}
                <span className="receipts__summary"> — {s.summary}</span>
              </li>
            ))}
        </ul>
      </div>
      <div className="qentry__actions">
        <CopyButton text={confirmYaml(loc)} label="Copy confirm YAML" />
        <CopyButton text={suppressYaml(loc)} label="Copy suppress YAML" />
      </div>
    </article>
  )
}

function QueueApp() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('arrived')
  const [selected, setSelected] = useState(() => new Set())
  const toggle = (key) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })

  useEffect(() => {
    fetch('./queue.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData, setError)
  }, [])

  const locations = data ? data.locations : []
  const built = data ? data.generated.slice(0, 10) : null
  // "New" means a signal arrived recently — including a new signal at a
  // location we already knew, which is where the stories converge.
  const arrived = (l) => l.last_arrival || l.first_seen
  const isNew = (l) => built && arrived(l) && daysBetween(arrived(l), built) <= NEW_DAYS
  const newCount = locations.filter(isNew).length

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    const matched = !q
      ? locations
      : locations.filter(
          (l) =>
            l.key.toLowerCase().includes(q) ||
            l.signals.some((s) => s.summary.toLowerCase().includes(q))
        )
    // queue.json arrives newest-activity-first; the other sorts are stable
    // re-orderings of that.
    const sorted = matched.slice()
    if (sort === 'arrived') {
      sorted.sort((a, b) => (arrived(b) || '').localeCompare(arrived(a) || ''))
    } else if (sort === 'strength') {
      sorted.sort((a, b) => strength(b) - strength(a))
    }
    return sorted
  }, [locations, query, sort])

  return (
    <div className="wrap">
      <header className="masthead">
        <div className="masthead__title">Coming Soon — editor queue</div>
        <div className="masthead__tag">internal · everything here is still public record</div>
      </header>

      <div className="topbar">
        <span>
          Verify what&rsquo;s moving in, then paste a block under{' '}
          <code>locations:</code> in data/overrides/locations.yaml. See these in the
          public design at <a href="./preview.html">preview.html</a>.
        </span>
        {data && <span className="updated">built {fmtDate(data.generated.slice(0, 10))}</span>}
      </div>

      <div className="filters">
        <label>
          Search{' '}
          <input
            className="qsearch"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="key or summary…"
          />
        </label>
        <label>
          Sort{' '}
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="arrived">Newest arrivals</option>
            <option value="strength">Strongest signals</option>
            <option value="activity">Latest activity</option>
          </select>
        </label>
        <span className="updated">
          {shown.length} of {locations.length} awaiting review
          {newCount > 0 && ` · ${newCount} new in the last ${NEW_DAYS} days`}
        </span>
      </div>

      {error && (
        <p className="notice notice--error">
          Couldn&rsquo;t load the queue ({String(error.message || error)}).
        </p>
      )}
      {data && locations.length === 0 && <p className="notice">Queue is empty — all caught up.</p>}
      {data && locations.length > 0 && shown.length === 0 && (
        <p className="notice">No entries match that search.</p>
      )}
      {selected.size > 0 && (
        <div className="bulkbar">
          <span>{selected.size} selected</span>
          <CopyButton
            text={bulkSuppressYaml(locations.filter((l) => selected.has(l.key)))}
            label={`Copy suppress YAML for ${selected.size}`}
          />
          <button className="copybtn" onClick={() => setSelected(new Set())}>
            Clear
          </button>
        </div>
      )}
      {shown.map((loc) => (
        <Entry
          key={loc.key}
          loc={loc}
          isNew={isNew(loc)}
          selected={selected.has(loc.key)}
          onToggle={() => toggle(loc.key)}
        />
      ))}
    </div>
  )
}

const el = document.getElementById('root')
;(el._root ||= createRoot(el)).render(<QueueApp />)
