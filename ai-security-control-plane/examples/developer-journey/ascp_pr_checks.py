#!/usr/bin/env python3
"""
ASCP developer-journey checks for pull-request CI (stdlib only).

1. Uploads dependency lockfiles to ASCP supply-chain (stub scanner / provenance).
2. Creates an assurance run against your staging OpenAI-compatible chat endpoint
   and fails the process if min_pass_rate is not met (fail_ci).

Environment:
  ASCP_BASE_URL          e.g. https://ascp.example.com (no trailing slash)
  ASCP_TOKEN             Bearer token: ASCP_API_KEY (admin) or tenant ascp_ten_...
  ASCP_TENANT_ID         Tenant id (path must match tenant token)
  ASCP_ASSURANCE_TARGET_URL   Staging URL ASCP POSTs test prompts to (required unless --supply-only)
  ASCP_MIN_PASS_RATE     Optional; default 0.7

Flags:
  --supply-only          Only upload lockfiles; do not run assurance.
  --assurance-only       Skip lockfile uploads.
  --require-lockfile     Exit 2 if no known lockfile exists in repo root.

Lockfiles detected (repo root): requirements.txt, Pipfile.lock, poetry.lock,
package-lock.json, pnpm-lock.yaml, yarn.lock, go.sum, Cargo.lock.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.error import URLError

LOCKFILE_CANDIDATES = [
    "requirements.txt",
    "Pipfile.lock",
    "poetry.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "go.sum",
    "Cargo.lock",
]
MAX_UPLOAD_BYTES = 4 * 1024 * 1024


def _req(
    method: str,
    url: str,
    *,
    token: str,
    data: bytes | None = None,
    json_body: dict | None = None,
    content_type: str | None = None,
    timeout: float = 120.0,
) -> tuple[int, bytes] | None:
    body = json.dumps(json_body).encode() if json_body is not None else data
    headers = {"Authorization": f"Bearer {token}"}
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    elif content_type:
        headers["Content-Type"] = content_type
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except URLError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None


def main() -> int:
    p = argparse.ArgumentParser(description="ASCP PR: supply upload + assurance fail_ci")
    p.add_argument("--root", type=Path, default=Path.cwd(), help="Repo root (default cwd)")
    p.add_argument("--supply-only", action="store_true")
    p.add_argument("--assurance-only", action="store_true")
    p.add_argument("--require-lockfile", action="store_true")
    args = p.parse_args()

    base = (os.environ.get("ASCP_BASE_URL") or "").strip().rstrip("/")
    token = (os.environ.get("ASCP_TOKEN") or "").strip()
    tenant = (os.environ.get("ASCP_TENANT_ID") or "").strip()
    target = (os.environ.get("ASCP_ASSURANCE_TARGET_URL") or "").strip()
    try:
        min_pass = float(os.environ.get("ASCP_MIN_PASS_RATE") or "0.7")
    except ValueError:
        print("ASCP_MIN_PASS_RATE must be a float", file=sys.stderr)
        return 2

    if not base or not token or not tenant:
        print(
            "Set ASCP_BASE_URL, ASCP_TOKEN, and ASCP_TENANT_ID.",
            file=sys.stderr,
        )
        return 2

    root: Path = args.root

    if not args.assurance_only:
        found: list[Path] = []
        for name in LOCKFILE_CANDIDATES:
            path = root / name
            if path.is_file():
                found.append(path)
        if args.require_lockfile and not found:
            print(
                "No lockfile found; add one of: " + ", ".join(LOCKFILE_CANDIDATES),
                file=sys.stderr,
            )
            return 2
        for path in found:
            raw = path.read_bytes()
            if len(raw) > MAX_UPLOAD_BYTES:
                print(f"Skip {path.name}: larger than {MAX_UPLOAD_BYTES} bytes", file=sys.stderr)
                continue
            from urllib.parse import quote

            fname = quote(path.name, safe="")
            url = f"{base}/v1/tenants/{quote(tenant, safe='')}/supply-chain/lockfile?filename={fname}"
            res = _req("POST", url, token=token, data=raw, content_type="application/octet-stream")
            if res is None:
                return 1
            code, body = res
            if code not in (200, 201, 204):
                print(
                    f"Lockfile upload failed {path.name}: HTTP {code} {body[:500]!r}",
                    file=sys.stderr,
                )
                return 1
            print(f"Uploaded supply lockfile: {path.name} (HTTP {code})")

        if not found:
            print("No lockfile matched; continuing (supply chain step skipped).")

    if args.supply_only:
        print("Supply-only mode; done.")
        return 0

    if not target:
        print(
            "ASCP_ASSURANCE_TARGET_URL is not set. "
            "Point it at a staging chat endpoint that accepts OpenAI-style POST JSON.",
            file=sys.stderr,
        )
        return 2

    create_url = f"{base}/v1/tenants/{tenant}/assurance-runs"
    payload = {
        "suite": "builtin-v0",
        "metadata": {
            "target_url": target,
            "min_pass_rate": min_pass,
        },
    }
    res = _req("POST", create_url, token=token, json_body=payload)
    if res is None:
        return 1
    code, body = res
    if code != 200:
        print(f"Create assurance run failed: HTTP {code} {body.decode(errors='replace')[:800]}", file=sys.stderr)
        return 1
    run_id = json.loads(body.decode())["run_id"]
    print(f"Created assurance run {run_id}")

    exec_url = f"{base}/v1/tenants/{tenant}/assurance-runs/{run_id}/execute?fail_ci=true"
    res = _req("POST", exec_url, token=token, json_body={})
    if res is None:
        return 1
    code, body = res
    out_txt = body.decode(errors="replace")
    if code == 422:
        print("Assurance did not meet min_pass_rate (fail_ci):", file=sys.stderr)
        print(out_txt[:2000], file=sys.stderr)
        return 1
    if code != 200:
        print(f"Execute failed: HTTP {code} {out_txt[:800]}", file=sys.stderr)
        return 1
    summary = json.loads(out_txt)
    print(
        "Assurance OK:",
        f"score={summary.get('score')} passed={summary.get('passed_count')}/{summary.get('total')} "
        f"ci_passed={summary.get('ci_passed')}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
