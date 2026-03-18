# Developer journey (PR CI)

This matches the PRD **Developer** path: **PR runs a supply upload + short red-team assurance**; the PR can **fail** if assurance scores below your threshold.

## What runs

| Step | What it does |
|------|----------------|
| **Supply (stub)** | Uploads dependency lockfiles from the repo to ASCP (`POST .../supply-chain/lockfile`). You get hashed artifacts and dashboard visibility—not CVE analysis yet. |
| **Assurance** | ASCP POSTs the **builtin-v0** scenario prompts to **your staging** URL (OpenAI-compatible chat JSON). If the pass rate is below **`min_pass_rate`**, `execute?fail_ci=true` returns **422** and CI fails. |

## What you need

1. **ASCP** deployed (or internal URL) with **`ASCP_API_KEY`** set; create a **tenant** and (recommended) a **tenant API token** scoped to that tenant.
2. **Staging app** that:
   - Accepts `POST` with JSON like `{ "model": "...", "messages": [{ "role": "user", "content": "..." }] }`.
   - Returns **200** with a body ASCP can score (jailbreak refusals + fake secret leak heuristics). A proxy to a real model is fine; a mock that always returns `"I cannot help with that"` will score well on jailbreak rows.

3. **Policy + trust** on that tenant: register the **model** id your staging uses and install a **policy** (`default@v1`) so gateway/evaluate match production rules if you later route staging through ASCP.

## GitHub Actions (copy into your app repo)

1. Copy **[examples/developer-journey/github-actions-pr.yml](../examples/developer-journey/github-actions-pr.yml)** → `.github/workflows/ascp-pr.yml`.
2. Repository **variable**: `ASCP_CI_ENABLED` = `true`.
3. Repository **secrets**:
   - `ASCP_BASE_URL` — e.g. `https://ascp.mycompany.com`
   - `ASCP_TOKEN` — admin key or `ascp_ten_...` tenant token
   - `ASCP_TENANT_ID` — must match the tenant in the token path
   - `ASCP_ASSURANCE_TARGET_URL` — staging chat URL (no path suffix required if the app expects POST at that URL; ASCP POSTs JSON to this URL as-is)
4. Optional **variable** `ASCP_MIN_PASS_RATE` (e.g. `0.85`); default in workflow is `0.7`.

## Local / other CI

Use the stdlib-only script (no `pip install`):

```bash
export ASCP_BASE_URL="https://..."
export ASCP_TOKEN="..."
export ASCP_TENANT_ID="my-app"
export ASCP_ASSURANCE_TARGET_URL="https://staging.my-app.com/v1/chat"  # your endpoint
export ASCP_MIN_PASS_RATE=0.7   # optional

python3 examples/developer-journey/ascp_pr_checks.py
```

Flags: `--supply-only`, `--assurance-only`, `--require-lockfile`.

## Failure modes

- **422 on execute**: Assurance score &lt; `min_pass_rate` (e.g. jailbreak not refused, or response matched secret-leak heuristic). Tune staging behavior or threshold.
- **401/403**: Wrong token or tenant mismatch.
- **Timeouts**: Set `ASCP_ASSURANCE_HTTP_TIMEOUT_SECONDS` on the server; staging must respond within that window.

## Next steps

- Point **staging** through ASCP **gateway** so assurance hits the same policy as prod.
- Tighten **`min_pass_rate`** toward `1.0` as prompts harden.
