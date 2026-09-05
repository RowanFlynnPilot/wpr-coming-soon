# Editor guide — confirming Coming Soon entries

The pipeline finds *signals* (permits, property sales, license applications) and
groups them by address. **Nothing is published until you confirm it here.**

## Workflow

1. Open the editor queue page (`/queue.html` on the deployed site) — every
   location sitting at `signal` status, with its receipts, sorted by newest
   arrivals or strongest signals. (`public/queue.json` is the raw file.)
2. Verify what's actually going in (call, drive by, check the license agenda).
3. Use the page's "Copy confirm YAML" button and paste the block under
   `locations:` in `locations.yaml` — the key is copied exactly:

   ```yaml
   "301 WASHINGTON ST|WAUSAU":
     status: coming_soon        # or: open
     name: "Example Coffee Co." # required once status is set
     category: restaurant       # freeform, keep it consistent
     note: "Confirmed by owner 8/12; targeting October."
   ```

4. Commit and push. A build runs on any push to this folder — the public page
   updates within a few minutes (the nightly run also picks it up).

## Other moves

- **Not a new opening** (remodel of an existing business, landlord maintenance):
  `suppress: true` — and nothing else in the block.
- **Now open:** change `status: open` and add `opened: 2026-10-01`.
- **Two keys are the same building** (address written two ways in different
  sources): add an `address_aliases:` entry mapping the variant to the
  canonical key.

The pipeline fails loudly on typos: unknown fields, a status without a name,
or an override pointing at an address with no signals all stop the build.
That's on purpose.
