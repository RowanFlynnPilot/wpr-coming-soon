// Shared display helpers for the public widget and the editor queue page.

export const KIND_LABELS = {
  sign_permit: 'Sign permit',
  new_commercial_construction: 'Construction permit',
  commercial_alteration: 'Building permit',
  commercial_sale: 'Property sale',
  alcohol_license_application: 'License application',
}

// "Aug 1" this year, "Aug 1, 2026" once the year has turned — the ledgers
// are accrue-only, so old receipts stay on screen for a long time.
export function fmtDate(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  const options = { month: 'short', day: 'numeric' }
  if (y !== new Date().getFullYear()) options.year = 'numeric'
  return new Date(y, m - 1, d).toLocaleDateString('en-US', options)
}

// The receipt reference shown after the kind + date, per source.
export function receiptRef(signal) {
  const r = signal.receipt
  if (signal.source === 'permit') return `#${r.permit_number}`
  if (signal.source === 'transfer') return `doc #${r.document_number}`
  if (signal.source === 'license') return r.body
  return null
}
