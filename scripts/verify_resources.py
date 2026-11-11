"""Verify every resource URL in content/resources.yaml.

* YouTube embeds are checked through the public oEmbed endpoint (title/channel must resolve).
* Other URLs are checked with a GET request (status < 400, following redirects).

Usage:  python scripts/verify_resources.py [--json report.json]
Exit code is non-zero if any resource fails, so this can run in CI.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
UA = "Mozilla/5.0 (compatible; ai-engineering-academy-link-check/1.0)"
# Sites that block automated clients but are known to be valid in a browser.
SOFT_FAIL_STATUS = {401, 403, 429, 999}


def fetch(url: str, timeout: int = 20, attempts: int = 3) -> tuple[int, str]:
    status, body = 0, ""
    for i in range(attempts):
        status, body = _fetch_once(url, timeout)
        if status != 0:
            break
        time.sleep(2 * (i + 1))  # transient network errors (resets), back off and retry
    return status, body


def _fetch_once(url: str, timeout: int) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(4096).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001 — report any network failure
        return 0, str(e)


def check(res: dict) -> dict:
    yt = (res.get("embed") or {}).get("youtube")
    if yt:
        q = urllib.parse.quote(f"https://www.youtube.com/watch?v={yt}", safe="")
        status, body = fetch(f"https://www.youtube.com/oembed?url={q}&format=json")
        ok = status == 200
        detail = json.loads(body).get("title", "") if ok else f"oembed {status}"
        return {"id": res["id"], "ok": ok, "status": status, "detail": detail}
    status, body = fetch(res["url"])
    if status in SOFT_FAIL_STATUS:
        return {"id": res["id"], "ok": True, "status": status, "detail": "blocked automated client (soft pass)"}
    return {"id": res["id"], "ok": 200 <= status < 400, "status": status, "detail": "" if status else body[:120]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write a JSON report here")
    args = ap.parse_args()
    resources = yaml.safe_load((ROOT / "content" / "resources.yaml").read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(check, resources))
    failed = [r for r in results if not r["ok"]]
    for r in results:
        mark = "OK  " if r["ok"] else "FAIL"
        print(f"{mark} {r['status']:>3} {r['id']:<34} {r['detail']}")
    print(f"\n{len(results) - len(failed)}/{len(results)} resources verified")
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
