# Editor guide — confirming Coming Soon entries

The pipeline finds *signals* (permits, property sales, license applications) and
groups them by address. **Nothing is published until you confirm it here.**

## Workflow

1. Open `public/queue.json` — every location sitting at `signal` status, with
   its receipts.
2. Verify what's actually going in (call, drive by, check the license agenda).
3. Add a block to `locations:` in `locations.yaml`, keyed by the location's
   `key` copied exactly from the queue:

   ```yaml
   "301 WASHINGTON ST|WAUSAU":
     status: coming_soon        # or: open
     name: "Example Coffee Co." # required once status is set
     category: restaurant       # freeform, keep it consistent
     note: "Confirmed by owner 8/12; targeting October."
   ```

4. Commit. The next build publishes it.

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
