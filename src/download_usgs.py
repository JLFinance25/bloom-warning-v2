"""
Download the Long Island USGS daily values named in PREREG section 3. Run only after the PREREG is locked.

    .venv/bin/python -I src/download_usgs.py

Writes one untouched RDB text file per station into data/raw/usgs_long_island/, plus a manifest with the
request URL, the time of the pull and each file's SHA-256. Nothing here cleans or changes a value.
USGS data is public domain; no account or key is used.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SITES = {
    "01311143": "Hog Island Channel at Island Park NY",
    "01310740": "Reynolds Channel at Point Lookout NY",
    "01304562": "Peconic River at County Hwy 105 at Riverhead NY",
    "01304650": "Shelter Island Sound at Shelter Island NY",
    "01303152": "West Harbor at Oyster Bay NWR at Bayville NY",
}
# chlorophyll, water temperature, salinity, dissolved oxygen, turbidity
PARAMETERS = ["32316", "00010", "90860", "00300", "63680"]
# daily maximum, minimum, mean
STATISTICS = ["00001", "00002", "00003"]
START, END = "2010-01-01", "2026-11-16"
SERVICE = "https://waterservices.usgs.gov/nwis/dv/"
OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "usgs_long_island"


def url_for(site: str) -> str:
    query = {
        "format": "rdb",
        "sites": site,
        "parameterCd": ",".join(PARAMETERS),
        "statCd": ",".join(STATISTICS),
        "startDT": START,
        "endDT": END,
    }
    return SERVICE + "?" + urllib.parse.urlencode(query)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"pulled_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "files": []}
    for site, name in SITES.items():
        target = OUT / f"usgs_dv_{site}.rdb"
        url = url_for(site)
        if target.exists():
            # Raw files are never overwritten. A file saved by an earlier, interrupted pull is kept as it is.
            body = target.read_bytes()
            print(f"{site}: keeping the file already saved (not downloaded again)")
        else:
            body = b""
            for attempt in range(1, 5):
                try:
                    request = urllib.request.Request(url, headers={"User-Agent": "research-script"})
                    with urllib.request.urlopen(request, timeout=120) as response:
                        body = response.read()
                    break
                except OSError as error:
                    print(f"{site}: attempt {attempt} failed ({error}); waiting before the next try")
                    time.sleep(10 * attempt)
            if not body.startswith(b"#"):
                sys.exit(f"Unexpected or empty reply for {site}: {body[:200]!r}")
            target.write_bytes(body)
        data_lines = sum(1 for line in body.splitlines() if line.startswith(b"USGS\t"))
        manifest["files"].append({
            "site": site, "name": name, "file": target.name, "url": url,
            "bytes": len(body), "data_rows": data_lines, "sha256": hashlib.sha256(body).hexdigest(),
        })
        print(f"{site}  {name}: {data_lines:,} daily rows, {len(body):,} bytes")
        time.sleep(1)
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {len(manifest['files'])} files and MANIFEST.json to {OUT}")


if __name__ == "__main__":
    main()
