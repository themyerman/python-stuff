"""Stub assurance runner: records scenarios, writes report artifact; live LLM calls TBD."""

from __future__ import annotations

import json
from typing import Any

from ascp.assurance.scenarios import scenarios_for_suite
from ascp.core.types import AuditEvent, AuditEventType
from ascp.storage.ports import ArtifactStore, AssuranceRunStore, AuditSink


def execute_builtin_stub_run(
    *,
    runs: AssuranceRunStore,
    artifacts: ArtifactStore,
    audit: AuditSink | None,
    tenant_id: str,
    run_id: str,
) -> dict[str, Any]:
    """
    Mark run completed with per-scenario rows (stub: no HTTP to customer app).
    Writes ``assurance/{run_id}/report.json``. Idempotent if already ``completed``.
    """
    rec = runs.get_run(run_id)
    if rec is None or rec.tenant_id != tenant_id:
        raise ValueError("run not found")

    if rec.status == "completed" and rec.metadata.get("runner") == "builtin-stub-v1":
        return {
            "run_id": run_id,
            "status": "completed",
            "idempotent": True,
            "scenario_count": len(rec.metadata.get("results", [])),
        }

    suite = str(rec.metadata.get("suite") or "builtin-v0")
    scenarios = scenarios_for_suite(suite)
    if not scenarios:
        runs.update_run(
            run_id,
            status="failed",
            metadata={
                **rec.metadata,
                "error": f"unknown_or_empty_suite:{suite}",
                "runner": "builtin-stub-v1",
            },
        )
        raise ValueError(f"unknown or empty suite: {suite!r}")

    results: list[dict[str, Any]] = []
    for s in scenarios:
        results.append(
            {
                "scenario_id": s["id"],
                "name": s["name"],
                "category": s["category"],
                "outcome": "pending_live_target",
                "detail": "Stub runner did not call a model; wire target_url + harness for real scores.",
                "prompt_preview": s["prompt"][:120] + ("…" if len(s["prompt"]) > 120 else ""),
            }
        )

    meta = {
        **rec.metadata,
        "suite": suite,
        "results": results,
        "runner": "builtin-stub-v1",
        "scenario_count": len(results),
    }
    runs.update_run(run_id, status="completed", metadata=meta)

    report = {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "suite": suite,
        "results": results,
    }
    key = f"assurance/{run_id}/report.json"
    artifacts.put_bytes(key, json.dumps(report, indent=2).encode("utf-8"))

    if audit is not None:
        audit.append(
            AuditEvent(
                event_type=AuditEventType.ASSURANCE_RUN,
                tenant_id=tenant_id,
                workspace_id=rec.workspace_id,
                run_id=run_id,
                payload={
                    "action": "execute_stub",
                    "suite": suite,
                    "scenario_count": len(results),
                    "artifact_key": key,
                },
            )
        )

    return {
        "run_id": run_id,
        "status": "completed",
        "suite": suite,
        "scenario_count": len(results),
        "report_key": key,
    }
