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
    '    category: restaurant',
    '    note: ""',
  ].join('\n')
}

function suppressYaml(loc) {
  return `  "${loc.key}":\n    suppress: true`
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

function Entry({ loc }) {
  return (
    <article className="card qentry">
      <div className="card__head">
        <h2 className="card__name qentry__key">{loc.key}</h2>
        <span className="status">{loc.signals.length} signal{loc.signals.length === 1 ? '' : 's'}</span>
      </div>
      <div className="card__meta">
        <span className="card__addr">
          {loc.address}, {loc.municipality}
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

  useEffect(() => {
    fetch('./queue.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData, setError)
  }, [])

  const locations = data ? data.locations : []
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return locations
    return locations.filter(
      (l) =>
        l.key.toLowerCase().includes(q) ||
        l.signals.some((s) => s.summary.toLowerCase().includes(q))
    )
  }, [locations, query])

  return (
    <div className="wrap">
      <header className="masthead">
        <div className="masthead__title">Coming Soon — editor queue</div>
        <div className="masthead__tag">internal · everything here is still public record</div>
      </header>

      <div className="topbar">
        <span>
          Verify what&rsquo;s moving in, then paste a block under{' '}
          <code>locations:</code> in data/overrides/locations.yaml.
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
        <span className="updated">
          {shown.length} of {locations.length} awaiting review
        </span>
      </div>

      {error && (
        <p className="notice notice--error">
          Couldn&rsquo;t load the queue ({String(error.message || error)}).
        </p>
      )}
      {data && locations.length === 0 && <p className="notice">Queue is empty — all caught up.</p>}
      {shown.map((loc) => (
        <Entry key={loc.key} loc={loc} />
      ))}
    </div>
  )
}

createRoot(document.getElementById('root')).render(<QueueApp />)
