// Single source of truth for branding + sponsorship. Same pattern as the
// paper's other widgets (see wpr-badgers-tracker/src/config.js).
export const CONFIG = {
  // WPR's typewriter press seal (served from public/), shown in the
  // masthead and footer — the same badge as the paper's other tools.
  WPR_BADGE: `${import.meta.env.BASE_URL}wpr-typewriter-badge.png`,

  CANONICAL_URL: 'https://wausaupilotandreview.com',

  // Sponsorship slots. null hides a slot entirely. Each slot is an object:
  //   { text: 'Presented by …',       required — the visible line
  //     href: 'https://sponsor.com',  optional — makes the slot tappable
  //     logo: 'https://…/mark.png' }  optional — small mark beside the text
  TITLE_SPONSOR: null, // banner slot, visible above the card list

  // Where sponsorship inquiries land (the WPR sales desk — Chris).
  SPONSOR_INQUIRY: 'weber.chris@wausaupilotandreview.com',
}

// SALES DEMO MODE — append ?demo and every OPEN sponsor slot renders a
// placeholder lockup so a prospect can see the placement in situ. Sold
// slots are never overridden; ordinary readers never see placeholders.
if (typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('demo')) {
  CONFIG.TITLE_SPONSOR = CONFIG.TITLE_SPONSOR || { text: 'Presented by Your Business Here' }
}
