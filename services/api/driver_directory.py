"""Client for the partner Driver Directory: driver profiles and verification status.

The Driver Directory is a partner system outside the Roadside API; every lookup is one
round trip to it. In this demo the partner is simulated in-process, so no extra service
has to be deployed:

- PARTNER_LATENCY_MS is the round-trip time of one lookup. Test environments (laptop,
  GKE sandboxes, UAT) use an instant stub (0). The production space sets the partner's
  real-world latency (deploy/prod/api.yaml), like a real dependency would have.
"""

from __future__ import annotations

import os
import time

LATENCY_S = int(os.environ.get("PARTNER_LATENCY_MS", "0")) / 1000

# What the partner knows about our drivers (demo data).
_DIRECTORY = {
    "Sam": {"verified": True, "checked_on": "2026-10-01"},
    "Maria": {"verified": True, "checked_on": "2026-09-14"},
}


def lookup(driver_name: str) -> dict:
    """Return the partner's profile for a driver. Unknown drivers come back unverified."""
    if LATENCY_S:
        time.sleep(LATENCY_S)  # simulated network round trip to the partner
    entry = _DIRECTORY.get(driver_name, {"verified": False, "checked_on": None})
    return {"name": driver_name, **entry}
